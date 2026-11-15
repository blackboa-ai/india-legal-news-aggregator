"""
Lightweight Embedding Service (< 80 MB RAM, No PyTorch / sentence-transformers)
India Legal News Aggregator - Free-Tier MVP Architecture

Generates 384-dimensional dense vector embeddings for legal text using:
1. Deterministic local feature hashing / TF-IDF projection (zero keys, < 1ms, 0 MB RAM)
2. Hugging Face Serverless Inference API (when HF_API_TOKEN is configured)
3. ONNX Runtime CPU inference (when quantized model weights exist on disk)

Ensures robust graceful fallback to deterministic 384-dim vectors in offline, test,
or quota-exhausted environments.
"""

import hashlib
import logging
import math
import re
from collections import Counter
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("app.services.embedding")

# Standard embedding dimensionality matching all-MiniLM-L6-v2
VECTOR_DIMENSION = 384

# HF Inference API Endpoint for all-MiniLM-L6-v2
HF_INFERENCE_URL = (
    "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
)


class EmbeddingService:
    """
    Asynchronous, memory-constrained 384-dimensional vector embedding generator.
    Strictly stays under 80 MB RAM by avoiding heavyweight deep learning frameworks.
    """

    def __init__(
        self,
        provider: str | None = None,
        hf_token: str | None = None,
        dimension: int = VECTOR_DIMENSION,
    ):
        self.provider = (provider or settings.EMBEDDING_PROVIDER).lower()
        self.hf_token = hf_token or settings.HF_API_TOKEN
        self.dimension = dimension
        self._onnx_session: Any | None = None
        self._tokenizer: Any | None = None
        self._onnx_initialized = False

    # --------------------------------------------------------------------------
    # Deterministic TF-IDF / Feature-Hashing Fallback (< 80 MB RAM, Zero Keys)
    # --------------------------------------------------------------------------
    def generate_deterministic_embedding(self, text: str, dim: int | None = None) -> list[float]:
        """
        Generates a deterministic, unit-normalized 384-dimensional dense vector
        using sublinear term-frequency feature hashing with unigrams and bigrams.

        Properties:
        - 100% deterministic: identical text produces identical vector.
        - Exact L2 unit-norm: ||v||_2 == 1.0 (ready for cosine distance <=>).
        - Semantic keyword preservation: texts sharing legal phrases, statute
          numbers, and party names exhibit positive cosine similarity.
        - Zero dependencies and zero external network calls.
        """
        target_dim = dim or self.dimension

        if not text or not text.strip():
            # Return uniform unit vector for empty input to prevent NaN / zero-division
            val = 1.0 / math.sqrt(target_dim)
            return [val] * target_dim

        # Clean and tokenize words (including alphanumeric statute citations like "438", "21")
        clean_text = text.lower()
        words = re.findall(r"[a-z0-9_]+", clean_text)
        if not words:
            val = 1.0 / math.sqrt(target_dim)
            return [val] * target_dim

        # Collect unigrams and bigrams to capture legal phrases (e.g., "anticipatory bail")
        tokens: list[str] = list(words)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")

        counts = Counter(tokens)
        vector = [0.0] * target_dim

        for token, count in counts.items():
            # Sublinear TF weight: 1 + ln(count)
            weight = 1.0 + math.log(count)

            # Boost explicit legal tokens (numbers, sections, articles)
            if re.match(r"^(section|\d+|article|rule|order|bail|quash|appeal|petitioner|respondent)", token):
                weight *= 1.5

            # Hash token with SHA-256 for deterministic bucket assignment
            token_bytes = token.encode("utf-8")
            hash_digest = hashlib.sha256(token_bytes).digest()

            # First 4 bytes determine index (0 to target_dim - 1)
            bucket_idx = int.from_bytes(hash_digest[:4], byteorder="big") % target_dim

            # Next 1 byte determines sign bit (+1 or -1) to prevent hash collisions from canceling
            sign = 1.0 if (hash_digest[4] & 0x01) == 0 else -1.0

            # Accumulate into dense vector
            vector[bucket_idx] += sign * weight

            # Secondary projection bucket for smoother representation
            secondary_idx = int.from_bytes(hash_digest[5:9], byteorder="big") % target_dim
            vector[secondary_idx] += (sign * 0.5) * weight

        # Compute Euclidean L2 norm
        norm = math.sqrt(sum(x * x for x in vector))
        if norm < 1e-9:
            val = 1.0 / math.sqrt(target_dim)
            return [val] * target_dim

        # Normalize to unit sphere (||v|| = 1.0)
        return [float(x / norm) for x in vector]

    # --------------------------------------------------------------------------
    # Optional ONNX Runtime Inference (< 90 MB RAM)
    # --------------------------------------------------------------------------
    def _init_onnx_if_available(self) -> bool:
        if self._onnx_initialized:
            return self._onnx_session is not None

        self._onnx_initialized = True
        try:
            from pathlib import Path

            import onnxruntime as ort
            from tokenizers import Tokenizer

            model_path = Path("backend/models/all-MiniLM-L6-v2.onnx")
            tokenizer_path = Path("backend/models/tokenizer.json")

            if model_path.exists() and tokenizer_path.exists():
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = 1
                opts.inter_op_num_threads = 1
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                self._onnx_session = ort.InferenceSession(str(model_path), opts)
                self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
                logger.info("Successfully loaded ONNX all-MiniLM-L6-v2 embedding model")
                return True
        except Exception as e:
            logger.debug("ONNX runtime embedding initialization skipped: %s", e)

        return False

    def _embed_onnx(self, text: str) -> list[float] | None:
        if not self._init_onnx_if_available() or not self._onnx_session or not self._tokenizer:
            return None

        try:
            import numpy as np

            encoding = self._tokenizer.encode(text[:512])
            input_ids = np.array([encoding.ids], dtype=np.int64)
            attention_mask = np.array([encoding.attention_mask], dtype=np.int64)
            token_type_ids = np.zeros_like(input_ids)

            inputs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            }

            outputs = self._onnx_session.run(None, inputs)
            # outputs[0] is token embeddings [batch, seq_len, 384]
            # Mean pooling over attention mask
            token_embeddings = outputs[0]
            mask_expanded = np.expand_dims(attention_mask, -1)
            sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=1)
            sum_mask = np.clip(mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
            mean_pooled = sum_embeddings / sum_mask

            # L2 normalize
            norm = np.linalg.norm(mean_pooled, axis=1, keepdims=True)
            normalized = mean_pooled / np.clip(norm, a_min=1e-9, a_max=None)
            return normalized[0].tolist()
        except Exception as err:
            logger.warning("ONNX embedding inference failed: %s", err)
            return None

    # --------------------------------------------------------------------------
    # Hugging Face Serverless Inference API (Free Tier)
    # --------------------------------------------------------------------------
    async def _embed_hf_api(self, text: str) -> list[float] | None:
        """
        Calls Hugging Face Inference API for all-MiniLM-L6-v2.
        Returns 384-dim list or None on error/quota/absence of token.
        """
        if not self.hf_token:
            return None

        headers = {
            "Authorization": f"Bearer {self.hf_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": text[:512],
            "options": {"wait_for_model": True},
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(HF_INFERENCE_URL, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    # Serverless feature extraction returns list of floats [384]
                    if isinstance(data, list) and len(data) == self.dimension and isinstance(data[0], (int, float)):
                        return [float(x) for x in data]
                    # Or nested list [[...]]
                    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                        flat = data[0]
                        if len(flat) == self.dimension:
                            return [float(x) for x in flat]
                else:
                    logger.warning("HF Inference API returned status %d: %s", response.status_code, response.text[:100])
        except Exception as err:
            logger.warning("HF Inference API request error: %s", err)

        return None

    # --------------------------------------------------------------------------
    # Public Async Interface
    # --------------------------------------------------------------------------
    async def get_embedding(self, text: str) -> list[float]:
        """
        Generates a 384-dimensional vector embedding for the input text.
        Employs configured provider with automatic fallback to deterministic projection.
        """
        # Try HF API if configured
        if self.provider == "hf" and self.hf_token:
            hf_vec = await self._embed_hf_api(text)
            if hf_vec is not None:
                return hf_vec

        # Try ONNX if configured
        if self.provider == "onnx":
            onnx_vec = self._embed_onnx(text)
            if onnx_vec is not None:
                return onnx_vec

        # Default / Graceful Fallback: Deterministic 384-dim TF-IDF projection
        return self.generate_deterministic_embedding(text)

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generates 384-dimensional vector embeddings for a batch of input texts.
        """
        return [await self.get_embedding(t) for t in texts]

    def get_embedding_sync(self, text: str) -> list[float]:
        """
        Synchronous convenience method utilizing deterministic embedding generator.
        Safe for offline testing and fast non-blocking evaluation.
        """
        return self.generate_deterministic_embedding(text)


# Singleton instance
embedding_service = EmbeddingService()
