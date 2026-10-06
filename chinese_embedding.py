r"""第3周Day5前置: 中文 embedding 模型（ONNX 版，不需要 torch / sentence-transformers）

模型: 智源研究院 BAAI/bge-small-zh-v1.5（ONNX 量化版，24MB）
位置: D:\workbuddy_data\models\bge-small-zh-onnx
原理: ONNX 推理 → 取 CLS 位输出 → L2 归一化，得到 512 维语义向量
"""
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MODEL_DIR = Path(r"D:\workbuddy_data\models\bge-small-zh-onnx")


class ChineseEmbedding:
    """把中文文本变成向量。对外提供 chromadb 需要的 __call__ 接口。"""

    def __init__(self, model_dir=MODEL_DIR):
        model_dir = Path(model_dir)
        self.model_dir = str(model_dir)
        self.tok = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tok.enable_padding(pad_id=0, pad_token="[PAD]")   # 批次内对齐长度
        self.tok.enable_truncation(max_length=512)             # 超长截断，防爆
        self.sess = ort.InferenceSession(
            str(model_dir / "model_quantized.onnx"),
            providers=["CPUExecutionProvider"],
        )

    def encode(self, texts):
        """输入 str 或 list[str]，输出 shape=(n, 512) 的归一化向量"""
        if isinstance(texts, str):
            texts = [texts]
        encs = self.tok.encode_batch(list(texts))
        ids = np.array([e.ids for e in encs], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
        out = self.sess.run(None, {
            "input_ids": ids,
            "attention_mask": mask,
            "token_type_ids": np.zeros_like(ids),
        })[0]
        cls = out[:, 0]                                        # CLS 池化
        return cls / np.linalg.norm(cls, axis=1, keepdims=True)  # L2 归一化

    def __call__(self, input):
        """chromadb 存文档时调用这个方法"""
        return self.encode(list(input)).tolist()

    def embed_query(self, input):
        """chromadb 用 query_texts 查询时调用（1.5.x 必须提供）"""
        return self.encode(list(input)).tolist()

    def build_from_config(self, config):
        """chromadb 从持久化配置恢复时调用"""
        return ChineseEmbedding(config.get("model_dir", MODEL_DIR))

    def get_config(self):
        return {"model_dir": self.model_dir}

    def name(self):
        return "bge-small-zh-onnx"


if __name__ == "__main__":
    emb = ChineseEmbedding()
    texts = ["怎么切换角色", "如何转换对话角色", "红烧肉怎么做", "python 老师"]
    vecs = emb.encode(texts)
    print("维度:", vecs.shape)
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            print(f"  {texts[i]}  vs  {texts[j]}  =  {float(vecs[i] @ vecs[j]):.3f}")
