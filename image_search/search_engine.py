import os
import numpy as np
from image_search.vectorizer import get_image_embedding

# حاول استيراد faiss، وإن لم يتوفر (خاصة على Windows) استخدم بديلًا مبنيًا على NumPy
try:
    import faiss  # type: ignore
    HAS_FAISS = True
except Exception:
    faiss = None  # type: ignore
    HAS_FAISS = False


class NumpyL2Index:
    """
    بديل بسيط لمؤشر FAISS يعتمد على NumPy ويستخدم مسافة L2.
    يحافظ على نفس واجهة الاستخدام العامة: add() و search().
    مناسب للأحجام الصغيرة والمتوسطة.
    """

    def __init__(self, dim: int):
        self.dim = dim
        self.vectors = None  # type: np.ndarray | None

    def add(self, x: np.ndarray):
        if x is None or len(x) == 0:
            return
        if self.vectors is None:
            self.vectors = x.astype("float32")
        else:
            self.vectors = np.vstack([self.vectors, x.astype("float32")])

    def search(self, queries: np.ndarray, k: int):
        if self.vectors is None or self.vectors.shape[0] == 0:
            qn = queries.shape[0]
            return (
                np.zeros((qn, 0), dtype="float32"),
                np.zeros((qn, 0), dtype="int64"),
            )

        q = queries.astype("float32")
        v = self.vectors.astype("float32")

        # d(q, v)^2 = ||q||^2 + ||v||^2 - 2 q·v
        q_norm = np.sum(q * q, axis=1, keepdims=True)  # (Q, 1)
        v_norm = np.sum(v * v, axis=1)  # (N,)
        distances = q_norm + v_norm[None, :] - 2.0 * (q @ v.T)  # (Q, N)

        k_eff = min(k, v.shape[0])
        # اختيار k الأقرب باستخدام argpartition ثم فرز جزئي
        idx_part = np.argpartition(distances, kth=k_eff - 1, axis=1)[:, :k_eff]  # (Q, k)
        row_idx = np.arange(distances.shape[0])[:, None]
        dist_part = distances[row_idx, idx_part]
        order = np.argsort(dist_part, axis=1)
        idx_sorted = idx_part[row_idx, order]
        dist_sorted = dist_part[row_idx, order]
        return dist_sorted.astype("float32"), idx_sorted.astype("int64")

class ImageSearchEngine:
    def __init__(self, images_folder: str):
        """
        images_folder: المسار إلى الجذر الذي يحتوي على جميع الصور (png و jpg) 
                       مثل "static/uploads".
        """
        # تحديد المسار الصحيح للصور بناءً على هيكل المشروع
        # نرجع مستوى واحد للخلف للوصول إلى المجلد الرئيسي للتطبيق
        self.images_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads')
        self.image_paths = []
        self.embeddings = None
        self.index = None

    def build_index(self):
        """
        يقرأ جميع الصور (.jpg/.jpeg/.png) ضمن جميع المجلدات الفرعية في self.images_folder،
        يحسب embedding لكل صورة، ثم يبني مؤشر FAISS.
        """
        all_embeddings = []
        
        # التأكد من وجود المجلد
        os.makedirs(self.images_folder, exist_ok=True)
        
        # استخدم os.walk ليزور المجلد والفرعيّات بحثًا عن ملفات الصور
        for root, dirs, files in os.walk(self.images_folder):
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    full_path = os.path.join(root, filename)
                    self.image_paths.append(full_path)
                    try:
                        emb = get_image_embedding(full_path)
                        all_embeddings.append(emb)
                    except Exception as e:
                        print(f"⚠️ فشل استخراج embedding من الصورة {full_path}: {e}")

        if not all_embeddings:
            print(f"تحذير: لم نعثر على أي صور في {self.images_folder} أو مجلداته الفرعية.")
            # إنشاء مصفوفة فارغة بدلاً من رفع استثناء
            self.embeddings = np.zeros((0, 512), dtype='float32')  # افتراض أن البعد هو 512
            self.index = faiss.IndexFlatL2(512) if HAS_FAISS else NumpyL2Index(512)
            return

        self.embeddings = np.array(all_embeddings).astype('float32')
        dim = self.embeddings.shape[1]  # عادةً 512 بعد CLIP
        self.index = faiss.IndexFlatL2(dim) if HAS_FAISS else NumpyL2Index(dim)
        self.index.add(self.embeddings)
        print(f"✅ تم بناء مؤشر FAISS لعدد {len(self.image_paths)} صورة في '{self.images_folder}' وكل مجلداته الفرعية.")

    def search(self, query_embedding: np.ndarray, k: int = 5):
        """
        يبحث عن k أقرب صور باستخدام مسافة L2 (Euclidean) للمصفوفة query_embedding.
        يُرجع قائمة بمسارات الصور المشابهة.
        """
        if self.embeddings is None or len(self.embeddings) == 0:
            return []  # إرجاع قائمة فارغة إذا لم تكن هناك صور
            
        query_vec = np.array([query_embedding]).astype('float32')
        distances, indices = self.index.search(query_vec, min(k, len(self.image_paths)))
        results = [self.image_paths[idx] for idx in indices[0] if idx < len(self.image_paths)]
        return results
