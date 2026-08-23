"""
이미 올라와 있는 이미지를 WebP 로 옮기고 크기를 채운다.

optimize_image 가 WebP 로 떨어뜨리게 된 건 나중이라, 그 전에 올라온 파일은
아직 PNG 다. 실측하면 차이가 크다 — 프로젝트 미디어 15.7MB 가 WebP 로는
2.3MB 다(JPEG 로는 3.8MB 라 WebP 가 38% 더 작다). 같은 김에 width/height 도
채운다. 그 값이 없으면 브라우저가 이미지 자리를 예약하지 못해 도착하는 순간
아래 내용을 밀어낸다(2026-05-01 측정 CLS 0.777).

이미 WebP 인 파일은 건드리지 않는다. 다시 인코딩하면 화질만 깎이고, 운영에서
한 번 돌린 뒤 결과가 미심쩍어 또 돌리는 일은 늘 생긴다.

    python manage.py convert_images_to_webp --dry-run
    python manage.py convert_images_to_webp
"""

from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management.base import BaseCommand

from menu.models import Category, MenuItem, SiteSettings
from menu.utils import optimize_image

# (모델, 필드명, max_width, quality) — models.py 의 save() 와 같은 값이어야 한다.
# 어긋나면 이 명령을 돌린 뒤 사장님이 사진을 다시 올릴 때 크기가 바뀐다.
TARGETS = [
    (SiteSettings, 'logo_image', 192, 90),
    (SiteSettings, 'intro_image', 1200, 85),
    (SiteSettings, 'side_image', 800, 85),
    (Category, 'category_image', 600, 80),
    (MenuItem, 'menu_image', 800, 80),
    (MenuItem, 'detail_image', 1200, 85),
]

# 크기 컬럼을 가진 필드. 레이아웃 흐름에 들어가 CLS 를 만드는 것들만 갖고 있다 —
# 로고는 파비콘이고 detail 은 눌러야 뜨는 오버레이라 자리를 밀지 않는다.
# 여기 없는 필드에 크기를 채우려 들면 AttributeError 로 명령 전체가 멈춘다.
HAS_DIMENSIONS = {'intro_image', 'side_image', 'category_image', 'menu_image'}


class Command(BaseCommand):
    help = '기존 이미지를 WebP 로 변환하고 width/height 를 채운다'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='바꾸지 않고 대상만 보여준다')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        converted = skipped = failed = filled = 0
        saved_bytes = 0

        for model, field, max_width, quality in TARGETS:
            for obj in model.objects.exclude(**{field: ''}).exclude(**{f'{field}__isnull': True}):
                image = getattr(obj, field)
                if not image:
                    continue
                if image.name.lower().endswith('.webp'):
                    # 포맷은 손댈 게 없지만 크기는 비어 있을 수 있다. 둘은 다른
                    # 일이다 — 크기를 채우자고 다시 인코딩하면 화질만 깎인다.
                    if field not in HAS_DIMENSIONS:
                        skipped += 1
                        continue
                    if self._backfill_dimensions(model, obj, field, dry):
                        filled += 1
                    else:
                        skipped += 1
                    continue

                label = f'{model.__name__}#{obj.pk} {field} {image.name}'
                try:
                    before = image.size
                except Exception:            # noqa: BLE001 — 파일이 사라진 행
                    self.stderr.write(f'  ! {label} 파일 없음')
                    failed += 1
                    continue

                if dry:
                    self.stdout.write(f'  [dry-run] {label} ({before / 1024:.0f}KB)')
                    converted += 1
                    continue

                try:
                    image.open()
                    optimized = optimize_image(image, max_width=max_width, quality=quality)
                    if not isinstance(optimized, InMemoryUploadedFile):
                        raise RuntimeError('optimize_image 가 원본을 그대로 돌려줬다')
                    setattr(obj, field, optimized)
                    # save() 가 optimize_image 를 또 부르지만 이미 WebP 라 결과는
                    # 같고, 그 안에서 record_image_dimensions 가 크기를 채운다.
                    obj.save()
                except Exception as e:       # noqa: BLE001 — 한 장의 실패가 나머지를 막지 않게
                    self.stderr.write(f'  ! {label} {e}')
                    failed += 1
                    continue

                after = getattr(obj, field).size
                saved_bytes += max(0, before - after)
                converted += 1
                self.stdout.write(
                    f'  o {label} → {getattr(obj, field).name} '
                    f'({before / 1024:.0f}KB → {after / 1024:.0f}KB)'
                )

        self.stdout.write(
            f'변환 {converted} / 크기만 채움 {filled} / 건너뜀 {skipped} / 실패 {failed}'
            + ('' if dry else f' · 절약 {saved_bytes / 1024 / 1024:.2f}MB')
        )

    def _backfill_dimensions(self, model, obj, field, dry):
        """
        이미 WebP 인 행의 width/height 만 채운다. 파일은 읽기만 한다.

        update() 로 컬럼만 쓴다. obj.save() 를 부르면 optimize_image 가 다시
        돌아 파일이 재인코딩된다.
        """
        if getattr(obj, f'{field}_width') and getattr(obj, f'{field}_height'):
            return False
        image = getattr(obj, field)
        try:
            with Image.open(image) as im:
                width, height = im.size
        except Exception as e:                    # noqa: BLE001 — 사라진 파일
            self.stderr.write(f'  ! {model.__name__}#{obj.pk} {field} 크기를 못 읽음 ({e})')
            return False
        if dry:
            self.stdout.write(f'  [dry-run] {model.__name__}#{obj.pk} {field} 크기 {width}x{height}')
            return True
        model.objects.filter(pk=obj.pk).update(**{f'{field}_width': width, f'{field}_height': height})
        return True
