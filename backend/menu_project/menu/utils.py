from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import os

def optimize_image(image_field, max_width=1200, quality=80):
    """이미지 최적화: WebP 포맷으로 변환하여 리사이즈 및 압축"""
    if not image_field:
        return image_field
    
    try:
        # Context Manager를 사용하여 파일 핸들 자동 닫기
        with Image.open(image_field) as img:
            # 원본 파일명에서 확장자를 webp로 변경
            original_name = image_field.name
            base_name, _ = os.path.splitext(original_name)
            webp_name = f"{base_name}.webp"
            
            # 투명도(알파 채널)가 있으면 RGBA로 유지, 없으면 RGB로 변환하여 파일 용량 최소화
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
            
            # 리사이즈
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # WebP로 저장
            output = BytesIO()
            img.save(output, format='WEBP', quality=quality)
            output.seek(0)
            
            return InMemoryUploadedFile(
                output, 'ImageField',
                webp_name,
                'image/webp',
                output.getbuffer().nbytes, None
            )
    except Exception as e:
        # 최적화 실패 시 원본 반환
        print(f"Image optimization to WebP failed: {e}")
        return image_field


def record_image_dimensions(instance, field_name):
    """
    `<field>_width` · `<field>_height` 에 실제 크기를 넣는다.

    optimize_image 가 줄인 *뒤*의 크기여야 한다. 원본 크기를 저장하면 브라우저가
    예약한 높이와 실제가 어긋나서, CLS 를 없애려던 것이 오히려 어긋난 자리를
    만든다.

    파일을 못 읽으면 조용히 비운다. 사장님이 이미지를 지웠거나 파일이 사라진
    행은 실제로 있고, 그것 때문에 저장이 통째로 실패하면 메뉴를 못 고친다.
    """
    image = getattr(instance, field_name, None)
    width = height = None
    if image:
        try:
            with Image.open(image) as im:
                width, height = im.size
        except Exception:
            width = height = None
        finally:
            try:
                image.seek(0)
            except Exception:
                pass
    setattr(instance, f'{field_name}_width', width)
    setattr(instance, f'{field_name}_height', height)
