"""
Post-Quantum Cryptography Detection Service
"""

import logging
from typing import List, Tuple

from ngfw_pqc_detector.models import CipherSuite, CryptoType, TLSClientHello

logger = logging.getLogger(__name__)


class PQCDetector:
    """
    Detects Post-Quantum Cryptography usage in TLS connections
    by analyzing ClientHello messages
    """

    # NIST-approved PQC algorithms
    PQC_KEY_EXCHANGE_ALGORITHMS = {
        "kyber512",
        "kyber768",
        "kyber1024",  # CRYSTALS-Kyber
        "mlkem512",
        "mlkem768",
        "mlkem1024",  # ML-KEM (standardized Kyber)
        "ntru",
        "ntruhrss701",
        "ntruhps2048509",
        "ntruhps2048677",
        "ntruhps4096821",
        "saber",
        "lightsaber",
        "saber",
        "firesaber",
    }

    # PQC Key Exchange Groups (Policy for Classification)
    PQC_KEY_EXCHANGE_GROUPS = {
        "kyber512",
        "kyber768",
        "kyber1024",
        "mlkem512",
        "mlkem768",
        "mlkem1024",
        "hybrid_x25519_kyber768",
        "hybrid_secp256r1_kyber768",
        "x25519_kyber768",
        "secp256r1_kyber768",
        "p256_kyber768",
    }

    PQC_SIGNATURE_ALGORITHMS = {
        "dilithium2",
        "dilithium3",
        "dilithium5",  # CRYSTALS-Dilithium
        "mldsa44",
        "mldsa65",
        "mldsa87",  # ML-DSA (standardized Dilithium)
        "falcon512",
        "falcon1024",  # Falcon
        "sphincs+",
        "sphincssha256128f",
        "sphincssha256192f",
        "sphincssha256256f",
    }

    # Classical algorithms for comparison
    CLASSICAL_KEY_EXCHANGE = {
        "ecdhe",
        "ecdh",
        "dhe",
        "rsa",
        "x25519",
        "x448",
        "secp256r1",
        "secp384r1",
        "secp521r1",
    }

    CLASSICAL_SIGNATURES = {
        "rsa",
        "ecdsa",
        "ed25519",
        "ed448",
        "rsa_pss_rsae_sha256",
        "rsa_pss_rsae_sha384",
        "rsa_pss_rsae_sha512",
        "ecdsa_secp256r1_sha256",
        "ecdsa_secp384r1_sha384",
        "ecdsa_secp521r1_sha512",
    }

    # Known PQC cipher suite codes (TLS 1.3)
    PQC_CIPHER_SUITES = {
        "0x1301": "TLS_AES_128_GCM_SHA256_KYBER512",
        "0x1302": "TLS_AES_256_GCM_SHA384_KYBER768",
        "0x1303": "TLS_CHACHA20_POLY1305_SHA256_KYBER768",
        "0xFE30": "TLS_MLKEM768_X25519_AES_128_GCM_SHA256",
        "0xFE31": "TLS_MLKEM768_X25519_AES_256_GCM_SHA384",
    }

    # Byte thresholds for heuristic detection
    # PQC algorithms like ML-KEM-768 use larger keys (~3KB more than classical ECDH)
    BYTE_THRESHOLD_PQC_SAFE = 8000  # > 8000 bytes indicates PQC
    BYTE_THRESHOLD_CLASSICAL_TLS13 = 5000  # 5000-8000 bytes indicates classical TLS 1.3
    # < 5000 bytes indicates legacy TLS

    def detect_crypto_type(
        self, client_hello: TLSClientHello, total_bytes: int = 0
    ) -> Tuple[CryptoType, float]:
        """
        Detect the cryptography type from ClientHello message

        Args:
            client_hello: TLS ClientHello message data
            total_bytes: Total bytes transferred in the connection (optional, for heuristic detection)

        Returns:
            Tuple of (CryptoType, confidence_score)
        """
        pqc_indicators = 0
        classical_indicators = 0
        total_indicators = 0

        # Check cipher suites
        for cipher in client_hello.cipher_suites:
            total_indicators += 1
            if cipher.code in self.PQC_CIPHER_SUITES:
                pqc_indicators += 1
            elif any(alg in cipher.name.lower() for alg in self.PQC_KEY_EXCHANGE_ALGORITHMS):
                pqc_indicators += 1
            else:
                classical_indicators += 1

        # Check supported groups (key exchange)
        for group in client_hello.supported_groups:
            total_indicators += 1
            group_lower = group.lower()
            if any(pqc_alg in group_lower for pqc_alg in self.PQC_KEY_EXCHANGE_ALGORITHMS):
                pqc_indicators += 1
            elif any(classical_alg in group_lower for classical_alg in self.CLASSICAL_KEY_EXCHANGE):
                classical_indicators += 1

        # Check signature algorithms
        for sig_alg in client_hello.signature_algorithms:
            total_indicators += 1
            sig_lower = sig_alg.lower()
            if any(pqc_sig in sig_lower for pqc_sig in self.PQC_SIGNATURE_ALGORITHMS):
                pqc_indicators += 1
            elif any(classical_sig in sig_lower for classical_sig in self.CLASSICAL_SIGNATURES):
                classical_indicators += 1

        # Check key share groups
        for key_share in client_hello.key_share_groups:
            total_indicators += 1
            key_share_lower = key_share.lower()
            if any(pqc_alg in key_share_lower for pqc_alg in self.PQC_KEY_EXCHANGE_ALGORITHMS):
                pqc_indicators += 1
            elif any(
                classical_alg in key_share_lower for classical_alg in self.CLASSICAL_KEY_EXCHANGE
            ):
                classical_indicators += 1

        # Determine crypto type
        if total_indicators == 0:
            # If no algorithm indicators found, use byte-based heuristic if available
            if total_bytes > 0:
                return self._detect_by_bytes(total_bytes)
            return CryptoType.UNKNOWN, 0.0

        pqc_ratio = pqc_indicators / total_indicators
        classical_ratio = classical_indicators / total_indicators

        # Algorithm-based detection (primary method)
        algorithm_result = None
        algorithm_confidence = 0.0

        # Hybrid: both PQC and classical algorithms present
        if pqc_indicators > 0 and classical_indicators > 0:
            confidence = min(pqc_ratio, classical_ratio) * 2  # Boost confidence for hybrid
            algorithm_result = CryptoType.HYBRID
            algorithm_confidence = min(confidence, 1.0)

        # Pure PQC
        elif pqc_indicators > 0:
            algorithm_result = CryptoType.PQC
            algorithm_confidence = pqc_ratio

        # Pure classical
        elif classical_indicators > 0:
            algorithm_result = CryptoType.CLASSICAL
            algorithm_confidence = classical_ratio

        # If we have byte data, use it to validate/enhance the algorithm-based detection
        if total_bytes > 0 and algorithm_result:
            byte_result, byte_confidence = self._detect_by_bytes(total_bytes)

            # If both methods agree, boost confidence
            if byte_result == algorithm_result:
                combined_confidence = min(algorithm_confidence * 1.2, 1.0)
                logger.debug(
                    f"Algorithm and byte-based detection agree: {algorithm_result.value}, confidence boosted to {combined_confidence:.2f}"
                )
                return algorithm_result, combined_confidence

            # If they disagree but algorithm confidence is high, trust algorithm
            elif algorithm_confidence > 0.7:
                logger.debug(
                    f"Algorithm detection (confidence {algorithm_confidence:.2f}) overrides byte heuristic"
                )
                return algorithm_result, algorithm_confidence

            # If algorithm confidence is low, consider byte-based result
            elif byte_confidence > algorithm_confidence:
                logger.debug(
                    f"Byte-based heuristic (confidence {byte_confidence:.2f}) overrides weak algorithm detection"
                )
                return byte_result, byte_confidence * 0.8  # Reduce confidence since it's heuristic

        if algorithm_result:
            return algorithm_result, algorithm_confidence

        return CryptoType.UNKNOWN, 0.0

    def classify_cipher_suite(self, cipher_code: str, cipher_name: str) -> CipherSuite:
        """
        Classify a cipher suite as PQC, classical, or hybrid

        Args:
            cipher_code: Cipher suite code (e.g., "0x1301")
            cipher_name: Cipher suite name

        Returns:
            CipherSuite object with classification
        """
        cipher_name_lower = cipher_name.lower()

        # Check if it's a known PQC cipher suite
        if cipher_code in self.PQC_CIPHER_SUITES:
            crypto_type = CryptoType.PQC
        # Check for PQC algorithms in the name
        elif any(pqc_alg in cipher_name_lower for pqc_alg in self.PQC_KEY_EXCHANGE_ALGORITHMS):
            crypto_type = (
                CryptoType.HYBRID
                if any(classical in cipher_name_lower for classical in self.CLASSICAL_KEY_EXCHANGE)
                else CryptoType.PQC
            )
        else:
            crypto_type = CryptoType.CLASSICAL

        return CipherSuite(
            code=cipher_code,
            name=cipher_name,
            crypto_type=crypto_type,
        )

    def classify_exchange_groups(
        self,
        supported_groups: List[str],
        key_share_groups: List[str],
        is_pqc_from_suricata: bool = False,
    ) -> dict:
        """
        Classify exchange groups into PQC, hybrid, and classical categories

        Args:
            supported_groups: List of supported groups from ClientHello
            key_share_groups: List of key share groups from ClientHello
            is_pqc_from_suricata: Flag from Suricata indicating if PQC is detected

        Returns:
            Dictionary with classification details
        """
        pqc_groups = []
        hybrid_groups = []
        classical_groups = []
        unknown_groups = []

        all_groups = set(supported_groups + key_share_groups)

        for group in all_groups:
            group_lower = group.lower()

            # Check if it's in PQC_KEY_EXCHANGE_GROUPS policy
            if any(pqc_group in group_lower for pqc_group in self.PQC_KEY_EXCHANGE_GROUPS):
                # Check if it's a hybrid group
                if "hybrid" in group_lower or any(
                    classical in group_lower
                    for classical in ["x25519", "secp256r1", "secp384r1", "p256", "p384"]
                ):
                    hybrid_groups.append(group)
                else:
                    pqc_groups.append(group)
            elif any(classical in group_lower for classical in self.CLASSICAL_KEY_EXCHANGE):
                classical_groups.append(group)
            elif "unknown" in group_lower:
                # Unknown algorithms - check Suricata's is_pqc flag
                if is_pqc_from_suricata:
                    # Suricata detected PQC, treat as PQC group
                    pqc_groups.append(group)
                    unknown_groups.append(group)
                else:
                    # No PQC indication, treat as classical
                    classical_groups.append(group)
                    unknown_groups.append(group)
            else:
                # Other unknown groups go to classical by default
                classical_groups.append(group)

        return {
            "pqc_groups": pqc_groups,
            "hybrid_groups": hybrid_groups,
            "classical_groups": classical_groups,
            "unknown_groups": unknown_groups,
            "total_groups": len(all_groups),
            "has_pqc": len(pqc_groups) > 0 or len(hybrid_groups) > 0,
        }

    def get_algorithm_details(self, client_hello: TLSClientHello) -> dict:
        """
        Extract detailed algorithm information from ClientHello

        Args:
            client_hello: TLS ClientHello message data

        Returns:
            Dictionary with algorithm details
        """
        return {
            "supported_groups": client_hello.supported_groups,
            "key_share_groups": client_hello.key_share_groups,
            "signature_algorithms": client_hello.signature_algorithms,
            "cipher_suites": [
                {"code": cipher.code, "name": cipher.name, "crypto_type": cipher.crypto_type.value}
                for cipher in client_hello.cipher_suites
            ],
        }

    def is_pqc_connection(self, client_hello: TLSClientHello) -> bool:
        """
        Quick check if connection uses any PQC algorithms

        Args:
            client_hello: TLS ClientHello message data

        Returns:
            True if PQC algorithms detected
        """
        crypto_type, confidence = self.detect_crypto_type(client_hello)
        return crypto_type in (CryptoType.PQC, CryptoType.HYBRID) and confidence > 0.5

    def _detect_by_bytes(self, total_bytes: int) -> Tuple[CryptoType, float]:
        """
        Heuristic detection based on total bytes transferred.
        PQC algorithms like ML-KEM-768 use larger keys (~3KB more than classical ECDH).

        Args:
            total_bytes: Total bytes transferred in the TLS connection

        Returns:
            Tuple of (CryptoType, confidence_score)
        """
        if total_bytes > self.BYTE_THRESHOLD_PQC_SAFE:
            # > 8000 bytes suggests PQC-compatible (ML-KEM-768 detected)
            confidence = min(0.6 + (total_bytes - self.BYTE_THRESHOLD_PQC_SAFE) / 10000, 0.85)
            logger.debug(
                f"Byte heuristic: {total_bytes} bytes > {self.BYTE_THRESHOLD_PQC_SAFE} → PQC (confidence: {confidence:.2f})"
            )
            return CryptoType.PQC, confidence

        elif total_bytes >= self.BYTE_THRESHOLD_CLASSICAL_TLS13:
            # 5000-8000 bytes suggests classical TLS 1.3 (ECDHE-P256)
            confidence = 0.5 + (total_bytes - self.BYTE_THRESHOLD_CLASSICAL_TLS13) / 10000
            logger.debug(
                f"Byte heuristic: {total_bytes} bytes in range {self.BYTE_THRESHOLD_CLASSICAL_TLS13}-{self.BYTE_THRESHOLD_PQC_SAFE} → Classical TLS 1.3 (confidence: {confidence:.2f})"
            )
            return CryptoType.CLASSICAL, confidence

        else:
            # < 5000 bytes suggests legacy TLS (RSA key exchange)
            confidence = 0.6
            logger.debug(
                f"Byte heuristic: {total_bytes} bytes < {self.BYTE_THRESHOLD_CLASSICAL_TLS13} → Legacy/Classical (confidence: {confidence:.2f})"
            )
            return CryptoType.CLASSICAL, confidence
