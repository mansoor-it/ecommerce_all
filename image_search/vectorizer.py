import torch
import open_clip
from PIL import Image

# اختيار الجهاز: لو لديك GPU سيكون cuda، وإلا يُستعمل cpu
device = "cuda" if torch.cuda.is_available() else "cpu"

# تحميل نموذج CLIP المحمّل مُسبقاً (ViT-B/32 على قاعدة laion2b)
model, _, preprocess = open_clip.create_model_and_transforms(
    'ViT-B-32', pretrained='laion2b_s34b_b79k'
)
model = model.to(device)

def get_image_embedding(image_path: str):
    """
    يُرجع متجه embedding (بُعد 512 مثلاً) للصورة الموجودة في المسار image_path.
    """
    image = Image.open(image_path).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)
    return image_features.cpu().numpy()[0]
