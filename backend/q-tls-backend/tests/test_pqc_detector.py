"""
Tests for PQC Detector Service
"""
import pytest
from ngfw_pqc_detector.services.pqc_detector import PQCDetector
from ngfw_pqc_detector.models import TLSClientHello, CipherSuite, CryptoType, TLSVersion


class TestPQCDetector:
    """Test cases for PQC detection"""

    def setup_method(self):
        """Setup test fixtures"""
        self.detector = PQCDetector()

    def test_classify_pqc_cipher_suite(self):
        """Test PQC cipher suite classification"""
        cipher = self.detector.classify_cipher_suite(
            cipher_code="0x1301",
            cipher_name="TLS_AES_128_GCM_SHA256_KYBER512"
        )
        assert cipher.crypto_type == CryptoType.PQC

    def test_classify_classical_cipher_suite(self):
        """Test classical cipher suite classification"""
        cipher = self.detector.classify_cipher_suite(
            cipher_code="0x1301",
            cipher_name="TLS_AES_128_GCM_SHA256"
        )
        assert cipher.crypto_type == CryptoType.CLASSICAL

    def test_detect_pqc_connection(self):
        """Test PQC connection detection"""
        client_hello = TLSClientHello(
            version=TLSVersion.TLS_1_3,
            cipher_suites=[
                CipherSuite(
                    code="0x1301",
                    name="TLS_AES_128_GCM_SHA256_KYBER512",
                    crypto_type=CryptoType.PQC
                )
            ],
            supported_groups=["kyber768", "x25519"],
            signature_algorithms=["dilithium3"],
        )

        crypto_type, confidence = self.detector.detect_crypto_type(client_hello)
        assert crypto_type in (CryptoType.PQC, CryptoType.HYBRID)
        assert confidence > 0.5

    def test_detect_classical_connection(self):
        """Test classical connection detection"""
        client_hello = TLSClientHello(
            version=TLSVersion.TLS_1_3,
            cipher_suites=[
                CipherSuite(
                    code="0x1301",
                    name="TLS_AES_128_GCM_SHA256",
                    crypto_type=CryptoType.CLASSICAL
                )
            ],
            supported_groups=["x25519", "secp256r1"],
            signature_algorithms=["ecdsa_secp256r1_sha256"],
        )

        crypto_type, confidence = self.detector.detect_crypto_type(client_hello)
        assert crypto_type == CryptoType.CLASSICAL
        assert confidence > 0.5

    def test_is_pqc_connection(self):
        """Test quick PQC check"""
        client_hello = TLSClientHello(
            version=TLSVersion.TLS_1_3,
            cipher_suites=[
                CipherSuite(
                    code="0xFE30",
                    name="TLS_MLKEM768_X25519_AES_128_GCM_SHA256",
                    crypto_type=CryptoType.HYBRID
                )
            ],
            supported_groups=["mlkem768", "x25519"],
        )

        assert self.detector.is_pqc_connection(client_hello) is True
