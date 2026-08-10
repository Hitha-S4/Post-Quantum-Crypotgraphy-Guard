/* Copyright (C) 2026 Open Information Security Foundation
 *
 * You can copy, redistribute or modify this Program under the terms of
 * the GNU General Public License version 2 as published by the Free
 * Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * version 2 along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
 * 02110-1301, USA.
 */

//! Post-Quantum Cryptography (PQC) TLS Detection Module
//!
//! This module provides detection and classification of PQC algorithms
//! in TLS handshakes, including:
//! - Kyber (ML-KEM) key exchange
//! - Hybrid modes (Kyber + classical ECDH)
//! - Encrypted Client Hello (ECH)
//! - Classical-only connections

use std::fmt;

/// TLS Extension Types for PQC detection
pub const TLS_EXT_SUPPORTED_GROUPS: u16 = 0x000a;
pub const TLS_EXT_KEY_SHARE: u16 = 0x0033;
pub const TLS_EXT_ENCRYPTED_CLIENT_HELLO: u16 = 0xfe0d;

/// Named Groups (RFC 8446 + PQC drafts)
/// Classical ECDH groups
pub const NAMED_GROUP_X25519: u16 = 0x001d;
pub const NAMED_GROUP_SECP256R1: u16 = 0x0017;
pub const NAMED_GROUP_SECP384R1: u16 = 0x0018;
pub const NAMED_GROUP_SECP521R1: u16 = 0x0019;

/// Kyber/ML-KEM groups (IETF draft values)
pub const NAMED_GROUP_MLKEM512: u16 = 0x0200;  // ML-KEM-512
pub const NAMED_GROUP_MLKEM768: u16 = 0x0201;  // ML-KEM-768
pub const NAMED_GROUP_MLKEM1024: u16 = 0x0202; // ML-KEM-1024

/// Hybrid Kyber groups (X25519 + Kyber)
pub const NAMED_GROUP_X25519_MLKEM768: u16 = 0x0203;
pub const NAMED_GROUP_X25519_MLKEM1024: u16 = 0x0204;

/// Hybrid Kyber groups (P-256 + Kyber)
pub const NAMED_GROUP_SECP256R1_MLKEM768: u16 = 0x0205;

/// Note: Group 0x11EC (4588) is often seen in real-world traffic but is not
/// a standardized group. It may be a vendor-specific or experimental group.
/// When mixed with classical groups, we classify based on the recognized groups.

/// PQC Posture Classification
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(C)]
pub enum PqcPosture {
    /// Pure post-quantum (Kyber/ML-KEM only)
    PqcPure,
    /// Hybrid PQC (Kyber + classical ECDH)
    PqcHybrid,
    /// Classical only (x25519, P-256, etc.)
    Classical,
    /// Encrypted Client Hello detected
    EchProtected,
    /// Unknown/large key shares that might be PQC
    UnknownPqc,
    /// Not yet determined
    Unknown,
}

impl fmt::Display for PqcPosture {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::PqcPure => write!(f, "PQC_PURE"),
            Self::PqcHybrid => write!(f, "PQC_HYBRID"),
            Self::Classical => write!(f, "CLASSICAL"),
            Self::EchProtected => write!(f, "ECH_PROTECTED"),
            Self::UnknownPqc => write!(f, "UNKNOWN_PQC"),
            Self::Unknown => write!(f, "UNKNOWN"),
        }
    }
}

impl PqcPosture {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::PqcPure => "PQC_PURE",
            Self::PqcHybrid => "PQC_HYBRID",
            Self::Classical => "CLASSICAL",
            Self::EchProtected => "ECH_PROTECTED",
            Self::UnknownPqc => "UNKNOWN_PQC",
            Self::Unknown => "UNKNOWN",
        }
    }
}

/// PQC Detection State
#[derive(Debug, Clone, PartialEq)]
pub struct PqcDetector {
    pub posture: PqcPosture,
    pub supported_groups: Vec<u16>,
    pub key_share_groups: Vec<u16>,
    pub has_ech: bool,
    pub has_kyber: bool,
    pub has_hybrid: bool,
    pub has_classical: bool,
}

impl Default for PqcDetector {
    fn default() -> Self {
        Self::new()
    }
}

impl PqcDetector {
    pub fn new() -> Self {
        Self {
            posture: PqcPosture::Unknown,
            supported_groups: Vec::new(),
            key_share_groups: Vec::new(),
            has_ech: false,
            has_kyber: false,
            has_hybrid: false,
            has_classical: false,
        }
    }

    /// Check if a named group is a pure Kyber/ML-KEM group
    pub fn is_kyber_group(group: u16) -> bool {
        matches!(
            group,
            NAMED_GROUP_MLKEM512 | NAMED_GROUP_MLKEM768 | NAMED_GROUP_MLKEM1024
        )
    }

    /// Check if a named group is a hybrid Kyber group
    pub fn is_hybrid_group(group: u16) -> bool {
        matches!(
            group,
            NAMED_GROUP_X25519_MLKEM768
                | NAMED_GROUP_X25519_MLKEM1024
                | NAMED_GROUP_SECP256R1_MLKEM768
        )
    }

    /// Check if a named group is classical ECDH
    pub fn is_classical_group(group: u16) -> bool {
        matches!(
            group,
            NAMED_GROUP_X25519
                | NAMED_GROUP_SECP256R1
                | NAMED_GROUP_SECP384R1
                | NAMED_GROUP_SECP521R1
        )
    }

    /// Get a human-readable name for a named group
    pub fn group_name(group: u16) -> &'static str {
        match group {
            // Classical ECDH groups
            NAMED_GROUP_X25519 => "X25519",
            NAMED_GROUP_SECP256R1 => "secp256r1",
            NAMED_GROUP_SECP384R1 => "secp384r1",
            NAMED_GROUP_SECP521R1 => "secp521r1",
            
            // Pure Kyber/ML-KEM groups
            NAMED_GROUP_MLKEM512 => "ML-KEM-512",
            NAMED_GROUP_MLKEM768 => "ML-KEM-768",
            NAMED_GROUP_MLKEM1024 => "ML-KEM-1024",
            
            // Hybrid Kyber groups
            NAMED_GROUP_X25519_MLKEM768 => "X25519+ML-KEM-768",
            NAMED_GROUP_X25519_MLKEM1024 => "X25519+ML-KEM-1024",
            NAMED_GROUP_SECP256R1_MLKEM768 => "secp256r1+ML-KEM-768",
            
            // Unknown/unrecognized groups
            0x11EC => "Unknown-0x11EC",
            _ => "Unknown",
        }
    }

    /// Add a supported group from the TLS extension
    pub fn add_supported_group(&mut self, group: u16) {
        if !self.supported_groups.contains(&group) {
            self.supported_groups.push(group);
        }

        // Update flags based on group type
        if Self::is_kyber_group(group) {
            self.has_kyber = true;
        } else if Self::is_hybrid_group(group) {
            self.has_hybrid = true;
        } else if Self::is_classical_group(group) {
            self.has_classical = true;
        }
    }

    /// Add a key share group (from actual key exchange)
    pub fn add_key_share_group(&mut self, group: u16) {
        if !self.key_share_groups.contains(&group) {
            self.key_share_groups.push(group);
        }
    }

    /// Mark that ECH extension was detected
    pub fn set_ech_detected(&mut self) {
        self.has_ech = true;
    }

    /// Classify the PQC posture based on collected data
    pub fn classify(&mut self) {
        // ECH takes precedence
        if self.has_ech {
            self.posture = PqcPosture::EchProtected;
            return;
        }

        // Check key shares first (actual negotiated algorithms)
        if !self.key_share_groups.is_empty() {
            let has_kyber_ks = self
                .key_share_groups
                .iter()
                .any(|&g| Self::is_kyber_group(g));
            let has_hybrid_ks = self
                .key_share_groups
                .iter()
                .any(|&g| Self::is_hybrid_group(g));
            let has_classical_ks = self
                .key_share_groups
                .iter()
                .any(|&g| Self::is_classical_group(g));

            if has_hybrid_ks {
                self.posture = PqcPosture::PqcHybrid;
                return;
            }
            if has_kyber_ks {
                self.posture = PqcPosture::PqcPure;
                return;
            }
            if has_classical_ks {
                self.posture = PqcPosture::Classical;
                return;
            }
        }

        // Fall back to supported groups
        // Prioritize based on what we've detected
        if self.has_hybrid {
            self.posture = PqcPosture::PqcHybrid;
        } else if self.has_kyber {
            self.posture = PqcPosture::PqcPure;
        } else if self.has_classical {
            // Even if there are unknown groups, if we have classical groups, classify as classical
            self.posture = PqcPosture::Classical;
        } else if !self.supported_groups.is_empty() {
            // No recognized PQC or classical groups, only unknown groups
            // This might be experimental PQC or unrecognized algorithms
            self.posture = PqcPosture::UnknownPqc;
        } else {
            // No groups at all
            self.posture = PqcPosture::Unknown;
        }
    }

    /// Get the current posture
    pub fn get_posture(&self) -> PqcPosture {
        self.posture
    }

    /// Check if connection uses any PQC algorithms
    pub fn is_pqc(&self) -> bool {
        matches!(
            self.posture,
            PqcPosture::PqcPure | PqcPosture::PqcHybrid | PqcPosture::UnknownPqc
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kyber_group_detection() {
        assert!(PqcDetector::is_kyber_group(NAMED_GROUP_MLKEM512));
        assert!(PqcDetector::is_kyber_group(NAMED_GROUP_MLKEM768));
        assert!(PqcDetector::is_kyber_group(NAMED_GROUP_MLKEM1024));
        assert!(!PqcDetector::is_kyber_group(NAMED_GROUP_X25519));
    }

    #[test]
    fn test_hybrid_group_detection() {
        assert!(PqcDetector::is_hybrid_group(NAMED_GROUP_X25519_MLKEM768));
        assert!(PqcDetector::is_hybrid_group(NAMED_GROUP_X25519_MLKEM1024));
        assert!(PqcDetector::is_hybrid_group(NAMED_GROUP_SECP256R1_MLKEM768));
        assert!(!PqcDetector::is_hybrid_group(NAMED_GROUP_X25519));
    }

    #[test]
    fn test_classical_group_detection() {
        assert!(PqcDetector::is_classical_group(NAMED_GROUP_X25519));
        assert!(PqcDetector::is_classical_group(NAMED_GROUP_SECP256R1));
        assert!(!PqcDetector::is_classical_group(NAMED_GROUP_MLKEM768));
    }

    #[test]
    fn test_pure_pqc_classification() {
        let mut detector = PqcDetector::new();
        detector.add_supported_group(NAMED_GROUP_MLKEM768);
        detector.classify();
        assert_eq!(detector.get_posture(), PqcPosture::PqcPure);
        assert!(detector.is_pqc());
    }

    #[test]
    fn test_hybrid_classification() {
        let mut detector = PqcDetector::new();
        detector.add_supported_group(NAMED_GROUP_X25519_MLKEM768);
        detector.classify();
        assert_eq!(detector.get_posture(), PqcPosture::PqcHybrid);
        assert!(detector.is_pqc());
    }

    #[test]
    fn test_classical_classification() {
        let mut detector = PqcDetector::new();
        detector.add_supported_group(NAMED_GROUP_X25519);
        detector.add_supported_group(NAMED_GROUP_SECP256R1);
        detector.classify();
        assert_eq!(detector.get_posture(), PqcPosture::Classical);
        assert!(!detector.is_pqc());
    }

    #[test]
    fn test_ech_takes_precedence() {
        let mut detector = PqcDetector::new();
        detector.add_supported_group(NAMED_GROUP_X25519);
        detector.set_ech_detected();
        detector.classify();
        assert_eq!(detector.get_posture(), PqcPosture::EchProtected);
    }

    #[test]
    fn test_key_share_precedence() {
        let mut detector = PqcDetector::new();
        // Supported groups suggest classical
        detector.add_supported_group(NAMED_GROUP_X25519);
        // But key share shows hybrid was actually negotiated
        detector.add_key_share_group(NAMED_GROUP_X25519_MLKEM768);
        detector.classify();
        assert_eq!(detector.get_posture(), PqcPosture::PqcHybrid);
    }

    #[test]
    fn test_classical_with_unknown_groups() {
        let mut detector = PqcDetector::new();
        // Mix of unknown group (like 0x11EC/4588) and classical groups
        detector.add_supported_group(0x11EC); // Unknown group
        detector.add_supported_group(NAMED_GROUP_X25519);
        detector.add_supported_group(NAMED_GROUP_SECP256R1);
        detector.add_supported_group(NAMED_GROUP_SECP384R1);
        detector.classify();
        // Should classify as CLASSICAL since all recognized groups are classical
        assert_eq!(detector.get_posture(), PqcPosture::Classical);
        assert!(!detector.is_pqc());
    }

    #[test]
    fn test_only_unknown_groups() {
        let mut detector = PqcDetector::new();
        // Only unknown groups
        detector.add_supported_group(0x11EC);
        detector.add_supported_group(0xAAAA);
        detector.classify();
        // Should classify as UNKNOWN_PQC (might be experimental)
        assert_eq!(detector.get_posture(), PqcPosture::UnknownPqc);
    }
}