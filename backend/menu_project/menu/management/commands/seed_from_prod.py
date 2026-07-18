"""
운영 DB(prod alias)에서 특정 식당(slug)의 데이터와 미디어를 개발 DB(default)로 복제한다.

설계 근거는 docs/superpowers/specs/2026-07-11-staging-environment-design.md 참고.
- bulk_create 를 사용해 save() 우회 → optimize_image 로 인한 파일명 재작성(HAZARD 2)과
  post_save 시그널로 인한 SiteSettings 중복 생성(HAZARD 1)을 동시에 회피한다.
- PK 를 보존하고 "삭제 후 재삽입"하므로 자기참조(Category.parent) PK 재매핑이 불필요하다.
- 파일 필드는 하드코딩하지 않고 _meta 로 동적 순회하여 하나도 빠뜨리지 않는다.

사용:  python manage.py seed_from_prod --slug bid
전제:  settings.DATABASES 에 'prod' alias 가 존재(PROD_DB_NAME 환경변수).
"""

import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from menu.models import Restaurant, SiteSettings, Category, MenuItem, MenuItemPairing

PROD_DB = 'prod'


def iter_file_field_names(instance):
    """모델 인스턴스에서 값이 있는 File/Image 필드의 저장 경로(name)를 순회한다."""
    for field in instance._meta.get_fields():
        if isinstance(field, models_file_fields()):
            value = getattr(instance, field.name, None)
            if value:
                name = getattr(value, 'name', None)
                if name:
                    yield name


def models_file_fields():
    from django.db.models import FileField
    # ImageField 는 FileField 의 서브클래스이므로 FileField 하나로 충분하다.
    return (FileField,)


class Command(BaseCommand):
    help = '운영 DB에서 지정한 식당(slug)의 데이터/미디어를 개발 DB로 복제한다.'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='복제할 식당 slug (예: bid)')
        parser.add_argument('--dry-run', action='store_true', help='변경 없이 계획만 출력')

    def handle(self, *args, **opts):
        slug = opts['slug']
        dry = opts['dry_run']

        if PROD_DB not in settings.DATABASES:
            raise CommandError(
                "'prod' DB alias 가 없습니다. PROD_DB_NAME 환경변수를 설정하세요."
            )
        if settings.DATABASES['default']['NAME'] == settings.DATABASES[PROD_DB]['NAME']:
            raise CommandError(
                '안전장치: default DB 와 prod DB 가 동일합니다. 개발 DB에서만 실행하세요.'
            )

        # 운영 미디어 경로는 환경변수로 받는다(별도 체크아웃이므로 경로가 다름).
        prod_media_root = os.environ.get('PROD_MEDIA_ROOT')
        if not prod_media_root:
            raise CommandError('PROD_MEDIA_ROOT 환경변수(운영 media 디렉토리 절대경로)가 필요합니다.')
        prod_media_root = Path(prod_media_root)
        dev_media_root = Path(settings.MEDIA_ROOT)

        # 1) 운영에서 객체 그래프를 읽는다.
        try:
            restaurant = Restaurant.objects.using(PROD_DB).get(slug=slug)
        except Restaurant.DoesNotExist:
            raise CommandError(f"운영 DB에 slug='{slug}' 식당이 없습니다.")

        site_settings = list(SiteSettings.objects.using(PROD_DB).filter(restaurant=restaurant))
        categories = list(Category.objects.using(PROD_DB).filter(restaurant=restaurant))
        menu_items = list(MenuItem.objects.using(PROD_DB).filter(restaurant=restaurant))
        menu_item_ids = [m.pk for m in menu_items]
        pairings = list(
            MenuItemPairing.objects.using(PROD_DB).filter(menu_item_id__in=menu_item_ids)
        )

        # 최상위 카테고리 → 하위 카테고리 순으로 정렬(자기참조 FK 삽입 순서 보장).
        top_categories = [c for c in categories if c.parent_id is None]
        # 부모가 먼저 오도록 위상정렬(깊이 우선).
        ordered_categories = self._order_by_parent(categories)

        self.stdout.write(
            f"[prod->dev] slug={slug}: SiteSettings={len(site_settings)}, "
            f"Category={len(categories)}(top={len(top_categories)}), "
            f"MenuItem={len(menu_items)}, Pairing={len(pairings)}"
        )

        # 2) 복사할 미디어 파일 목록 수집(모든 File/Image 필드 동적 순회).
        media_names = set()
        for obj in [restaurant, *site_settings, *categories, *menu_items, *pairings]:
            for name in iter_file_field_names(obj):
                media_names.add(name)
        self.stdout.write(f"복사 대상 미디어 파일: {len(media_names)}개")

        if dry:
            self.stdout.write(self.style.WARNING('--dry-run: 실제 변경 없음'))
            missing = [n for n in media_names if not (prod_media_root / n).exists()]
            if missing:
                self.stdout.write(self.style.WARNING(f"운영에 없는 파일 {len(missing)}개: {missing[:5]}"))
            return

        # 3) 미디어 파일을 먼저 복사(HAZARD 2: 레코드 저장 전에 파일이 있어야 함).
        copied, missing = 0, 0
        for name in media_names:
            src = prod_media_root / name
            dst = dev_media_root / name
            if not src.exists():
                missing += 1
                self.stderr.write(f"  누락(운영에 없음): {name}")
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        self.stdout.write(f"미디어 복사 완료: {copied}개 (누락 {missing}개)")

        # 4) dev DB에 삽입(트랜잭션). 기존 slug 데이터 삭제 후 PK 보존 재삽입.
        with transaction.atomic(using='default'):
            # 삭제: Restaurant 삭제가 SiteSettings/Category/MenuItem 을 CASCADE 로 정리한다.
            # (MenuItemPairing 은 MenuItem CASCADE 로 함께 삭제)
            existing = Restaurant.objects.filter(slug=slug).first()
            if existing:
                existing.delete()  # dev 기준. CASCADE 정리.
                self.stdout.write(f"기존 dev 데이터 삭제(slug={slug})")

            # bulk_create: save() 미호출 → optimize_image / post_save 시그널 우회.
            Restaurant.objects.bulk_create([restaurant])
            SiteSettings.objects.bulk_create(site_settings)
            # 카테고리는 부모→자식 순으로 나눠 넣는다(자기참조 FK 무결성).
            for depth_batch in ordered_categories:
                Category.objects.bulk_create(depth_batch)
            MenuItem.objects.bulk_create(menu_items)
            MenuItemPairing.objects.bulk_create(pairings)

        self.stdout.write(self.style.SUCCESS(
            f"완료: slug={slug} → dev DB. "
            f"Restaurant 1, SiteSettings {len(site_settings)}, Category {len(categories)}, "
            f"MenuItem {len(menu_items)}, Pairing {len(pairings)}"
        ))

    @staticmethod
    def _order_by_parent(categories):
        """카테고리를 부모가 자식보다 먼저 오도록 깊이별 배치 리스트로 반환."""
        by_id = {c.pk: c for c in categories}
        batches = []
        placed = set()
        # 깊이 0: parent 가 없거나 부모가 이 집합 밖(있어선 안 되지만 방어적으로).
        remaining = list(categories)
        while remaining:
            batch = [
                c for c in remaining
                if c.parent_id is None or c.parent_id in placed or c.parent_id not in by_id
            ]
            if not batch:
                # 순환(있어선 안 됨) → 남은 것 그대로 넣어 무한루프 방지.
                batch = remaining
            batches.append(batch)
            for c in batch:
                placed.add(c.pk)
            remaining = [c for c in remaining if c.pk not in placed]
        return batches
