"""Drive media uploads for the Feishu service.

Used to attach covers (and any other binary asset) to Bitable records.
Implements the multipart ``drive/v1/medias/upload_all`` API.
"""

import os
import mimetypes


class UploadMixin:
    """Cover-image upload to Feishu Drive."""

    def upload_image(self, image_path):
        """Upload image to Feishu Drive and return file_token.

        Uses the media upload API to upload file to Feishu,
        returns file_token that can be used in attachment fields.
        """
        if not os.path.exists(image_path):
            print(f"⚠️ Image not found: {image_path}")
            return None

        # Get file info
        file_name = os.path.basename(image_path)
        file_size = os.path.getsize(image_path)
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = 'image/jpeg'

        # Upload to Feishu media
        url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"

        with open(image_path, 'rb') as f:
            files = {
                'file': (file_name, f, mime_type)
            }
            data = {
                'file_name': file_name,
                'parent_type': 'bitable_image',
                'parent_node': self.config.get('feishu', self.config).get('base_id'),
                'size': str(file_size)
            }

            try:
                response = self.session.post(
                    url,
                    headers=self._auth_header(),
                    files=files,
                    data=data,
                    timeout=60
                )
                result = response.json()

                if result.get('code') == 0:
                    file_token = result.get('data', {}).get('file_token')
                    print(f"   📷 Uploaded: {file_name[:30]}...")
                    return file_token
                else:
                    print(f"⚠️ Upload failed: {result.get('msg', 'Unknown error')}")
                    return None
            except Exception as e:
                print(f"⚠️ Upload error: {e}")
                return None
