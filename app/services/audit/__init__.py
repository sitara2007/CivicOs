"""Audit service public exports."""

from app.services.audit.hash_chain import GENESIS_HASH, compute_prev_hash

__all__ = ["GENESIS_HASH", "compute_prev_hash"]
