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
