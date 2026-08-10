/* Copyright (C) 2025 Open Information Security Foundation
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

// Author: Sascha Steinbiss <sascha@steinbiss.name>

*/

use libc::c_uchar;
use std::ffi::CStr;
use std::os::raw::c_char;
use tls_parser::{TlsCipherSuiteID, TlsExtensionType, TlsVersion};

use crate::jsonbuilder::{JsonBuilder, JsonError};
use crate::pqc_tls::PqcDetector;
use crate::tls_version::SCTlsVersion;

#[derive(Debug, PartialEq)]
pub struct HandshakeParams {
    pub(crate) tls_version: Option<TlsVersion>,
    pub(crate) ciphersuites: Vec<TlsCipherSuiteID>,
    pub(crate) extensions: Vec<TlsExtensionType>,
    pub(crate) signature_algorithms: Vec<u16>,
    pub(crate) domain: bool,
    pub(crate) alpns: Vec<Vec<u8>>,
    pub(crate) quic: bool,
    pub(crate) pqc_detector: PqcDetector,
}

impl Default for HandshakeParams {
    fn default() -> Self {
        Self::new()
    }
}

impl HandshakeParams {
    #[inline]
    pub(crate) fn is_grease(val: u16) -> bool {
        match val {
            0x0a0a | 0x1a1a | 0x2a2a | 0x3a3a | 0x4a4a | 0x5a5a | 0x6a6a | 0x7a7a | 0x8a8a
            | 0x9a9a | 0xaaaa | 0xbaba | 0xcaca | 0xdada | 0xeaea | 0xfafa => true,
            _ => false,
        }
    }

    fn new() -> Self {
        Self {
            tls_version: None,
            ciphersuites: Vec::with_capacity(20),
            extensions: Vec::with_capacity(20),
            signature_algorithms: Vec::with_capacity(20),
            domain: false,
            alpns: Vec::with_capacity(4),
            quic: false,
            pqc_detector: PqcDetector::new(),
        }
    }

    pub(crate) fn set_tls_version(&mut self, version: TlsVersion) {
        if Self::is_grease(u16::from(version)) {
            return;
        }
        // Track maximum of seen TLS versions
        match self.tls_version {
            None => {
                self.tls_version = Some(version);
            }
            Some(cur_version) => {
                if u16::from(version) > u16::from(cur_version) {
                    self.tls_version = Some(version);
                }
            }
        }
    }

    pub fn add_alpn(&mut self, alpn: &[u8]) {
        if alpn.is_empty() {
            return;
        }
        self.alpns.push(alpn.to_vec());
    }

    pub(crate) fn add_cipher_suite(&mut self, cipher: TlsCipherSuiteID) {
        if Self::is_grease(u16::from(cipher)) {
            return;
        }
        self.ciphersuites.push(cipher);
    }

    pub(crate) fn add_extension(&mut self, ext: TlsExtensionType) {
        if Self::is_grease(u16::from(ext)) {
            return;
        }
        if ext == TlsExtensionType::ServerName {
            self.domain = true;
        }
        
        // Check for ECH extension
        if u16::from(ext) == crate::pqc_tls::TLS_EXT_ENCRYPTED_CLIENT_HELLO {
            self.pqc_detector.set_ech_detected();
        }
        
        self.extensions.push(ext);
    }

    pub(crate) fn add_signature_algorithm(&mut self, sigalgo: u16) {
        if Self::is_grease(sigalgo) {
            return;
        }
        self.signature_algorithms.push(sigalgo);
    }

    /// Add a supported group for PQC detection
    pub(crate) fn add_supported_group(&mut self, group: u16) {
        if Self::is_grease(group) {
            return;
        }
        self.pqc_detector.add_supported_group(group);
    }

    /// Add a key share group for PQC detection
    pub(crate) fn add_key_share_group(&mut self, group: u16) {
        if Self::is_grease(group) {
            return;
        }
        self.pqc_detector.add_key_share_group(group);
    }

    /// Classify PQC posture
    pub(crate) fn classify_pqc(&mut self) {
        self.pqc_detector.classify();
    }

    fn log_alpns(&self, js: &mut JsonBuilder, key: &str) -> Result<(), JsonError> {
        if self.alpns.is_empty() {
            return Ok(());
        }
        js.open_array(key)?;

        for v in &self.alpns {
            js.append_string_from_bytes(v)?;
        }
        js.close()?;
        Ok(())
    }

    fn log_version(&self, js: &mut JsonBuilder) -> Result<(), JsonError> {
        let vers = self.tls_version.map(|v| v.0).unwrap_or_default();
        let ver_str = SCTlsVersion::try_from(vers).map_err(|_| JsonError::InvalidState)?;
        js.set_string("version", ver_str.as_str())?;
        Ok(())
    }

    fn log_exts(&self, js: &mut JsonBuilder) -> Result<(), JsonError> {
        if self.extensions.is_empty() {
            return Ok(());
        }
        js.open_array("exts")?;

        for v in &self.extensions {
            js.append_uint(v.0.into())?;
        }
        js.close()?;
        Ok(())
    }

    fn log_first_cipher(&self, js: &mut JsonBuilder) -> Result<(), JsonError> {
        let chosen = self.ciphersuites.first().map(|&v| *v).unwrap_or(0);
        js.set_uint("cipher", chosen)?;
        Ok(())
    }

    fn log_ciphers(&self, js: &mut JsonBuilder) -> Result<(), JsonError> {
        if self.ciphersuites.is_empty() {
            return Ok(());
        }
        js.open_array("ciphers")?;

        for v in &self.ciphersuites {
            js.append_uint(v.0.into())?;
        }
        js.close()?;
        Ok(())
    }

    fn log_sig_algs(&self, js: &mut JsonBuilder) -> Result<(), JsonError> {
        if self.signature_algorithms.is_empty() {
            return Ok(());
        }
        js.open_array("sig_algs")?;

        for v in &self.signature_algorithms {
            js.append_uint(*v as u64)?;
        }
        js.close()?;
        Ok(())
    }

    fn log_pqc_posture(&self, js: &mut JsonBuilder) -> Result<(), JsonError> {
        js.set_string("pqc_posture", self.pqc_detector.get_posture().as_str())?;
        Ok(())
    }

    fn log_pqc_details(&self, js: &mut JsonBuilder) -> Result<(), JsonError> {
        if self.pqc_detector.supported_groups.is_empty() {
            return Ok(());
        }

        js.open_object("pqc")?;
        js.set_string("posture", self.pqc_detector.get_posture().as_str())?;
        js.set_bool("is_pqc", self.pqc_detector.is_pqc())?;
        js.set_bool("has_ech", self.pqc_detector.has_ech)?;

        if !self.pqc_detector.supported_groups.is_empty() {
            js.open_array("supported_groups")?;
            for &group in &self.pqc_detector.supported_groups {
                js.append_uint(group as u64)?;
            }
            js.close()?;
            
            // Add human-readable group names
            js.open_array("supported_groups_names")?;
            for &group in &self.pqc_detector.supported_groups {
                js.append_string(crate::pqc_tls::PqcDetector::group_name(group))?;
            }
            js.close()?;
        }

        if !self.pqc_detector.key_share_groups.is_empty() {
            js.open_array("key_share_groups")?;
            for &group in &self.pqc_detector.key_share_groups {
                js.append_uint(group as u64)?;
            }
            js.close()?;
            
            // Add human-readable group names
            js.open_array("key_share_groups_names")?;
            for &group in &self.pqc_detector.key_share_groups {
                js.append_string(crate::pqc_tls::PqcDetector::group_name(group))?;
            }
            js.close()?;
        }

        js.close()?;
        Ok(())
    }
}

// Objects used to allow C to call into this struct via the below C ABI
// that enables the return of a u8 pointer and length
#[repr(C)]
pub struct CStringData {
    data: *const u8,
    len: usize,
}

#[no_mangle]
pub extern "C" fn SCTLSHandshakeNew() -> *mut HandshakeParams {
    let hs = Box::new(HandshakeParams::new());
    Box::into_raw(hs)
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeIsEmpty(hs: & HandshakeParams) -> bool {
    *hs == HandshakeParams::default()
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeSetTLSVersion(hs: &mut HandshakeParams, version: u16) {
    hs.set_tls_version(TlsVersion(version));
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeAddCipher(hs: &mut HandshakeParams, cipher: u16) {
    hs.add_cipher_suite(TlsCipherSuiteID(cipher));
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeAddExtension(hs: &mut HandshakeParams, ext: u16) {
    hs.add_extension(TlsExtensionType(ext));
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeAddSigAlgo(hs: &mut HandshakeParams, sigalgo: u16) {
    hs.add_signature_algorithm(sigalgo);
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeAddALPN(
    hs: &mut HandshakeParams, alpn: *const c_char, len: u16,
) {
    let b: &[u8] = std::slice::from_raw_parts(alpn as *const c_uchar, len as usize);
    hs.add_alpn(b);
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeFree(hs: &mut HandshakeParams) {
    let hs: Box<HandshakeParams> = Box::from_raw(hs);
    std::mem::drop(hs);
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeLogVersion(hs: &HandshakeParams, js: *mut JsonBuilder) -> bool {
    if js.is_null() {
        return false;
    }
    return hs.log_version(js.as_mut().unwrap()).is_ok()
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeLogCiphers(hs: &HandshakeParams, js: *mut JsonBuilder) -> bool {
    if js.is_null() {
        return false;
    }
    return hs.log_ciphers(js.as_mut().unwrap()).is_ok()
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeLogFirstCipher(hs: &HandshakeParams, js: *mut JsonBuilder) -> bool {
    if js.is_null() {
        return false;
    }
    return hs.log_first_cipher(js.as_mut().unwrap()).is_ok()
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeLogExtensions(hs: &HandshakeParams, js: *mut JsonBuilder) -> bool {
    if js.is_null() {
        return false;
    }
    return hs.log_exts(js.as_mut().unwrap()).is_ok()
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeLogSigAlgs(hs: &HandshakeParams, js: *mut JsonBuilder) -> bool {
    if js.is_null() {
        return false;
    }
    return hs.log_sig_algs(js.as_mut().unwrap()).is_ok()
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeLogALPNs(
    hs: &HandshakeParams, js: *mut JsonBuilder, ptr: *const c_char
) -> bool {
    if js.is_null() {
        return false;
    }

    if let Ok(key) = CStr::from_ptr(ptr).to_str() {
        hs.log_alpns(js.as_mut().unwrap(), key).is_ok()
    } else {
        false
    }
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeAddSupportedGroup(hs: &mut HandshakeParams, group: u16) {
    hs.add_supported_group(group);
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeAddKeyShareGroup(hs: &mut HandshakeParams, group: u16) {
    hs.add_key_share_group(group);
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeClassifyPQC(hs: &mut HandshakeParams) {
    hs.classify_pqc();
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeLogPQCPosture(
    hs: &HandshakeParams, js: *mut JsonBuilder,
) -> bool {
    if js.is_null() {
        return false;
    }
    hs.log_pqc_posture(js.as_mut().unwrap()).is_ok()
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeLogPQCDetails(
    hs: &HandshakeParams, js: *mut JsonBuilder,
) -> bool {
    if js.is_null() {
        return false;
    }
    hs.log_pqc_details(js.as_mut().unwrap()).is_ok()
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeGetPQCPosture(hs: &HandshakeParams) -> *const c_char {
    let posture_str = hs.pqc_detector.get_posture().as_str();
    posture_str.as_ptr() as *const c_char
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeIsPQC(hs: &HandshakeParams) -> bool {
    hs.pqc_detector.is_pqc()
}

#[no_mangle]
pub unsafe extern "C" fn SCTLSHandshakeGetALPN(
    hs: &HandshakeParams, idx: u32, out: *mut CStringData,
) -> bool {
    if out.is_null() {
        return false;
    }
    if let Some(alpn) = hs.alpns.get(idx as usize) {
        *out = CStringData {
            data: alpn.as_ptr(),
            len: alpn.len(),
        };
        true
    } else {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_grease() {
        let mut alpn = "foobar".as_bytes();
        let mut len = alpn.len();
        let v: u16 = ((alpn[0] as u16) << 8) | alpn[len - 1] as u16;
        assert!(!HandshakeParams::is_grease(v));

        alpn = &[0x0a, 0x0a];
        len = alpn.len();
        let v: u16 = ((alpn[0] as u16) << 8) | alpn[len - 1] as u16;
        assert!(HandshakeParams::is_grease(v));
    }

    #[test]
    fn test_tlsversion_max() {
        let mut hs = HandshakeParams::new();
        assert_eq!(hs.tls_version, None);
        hs.set_tls_version(TlsVersion::Ssl30);
        assert_eq!(hs.tls_version, Some(TlsVersion::Ssl30));
        hs.set_tls_version(TlsVersion::Tls12);
        assert_eq!(hs.tls_version, Some(TlsVersion::Tls12));
        hs.set_tls_version(TlsVersion::Tls10);
        assert_eq!(hs.tls_version, Some(TlsVersion::Tls12));
    }

    #[test]
    fn test_add_cipher_suite_filters_grease() {
        let mut hs = HandshakeParams::new();
        hs.add_cipher_suite(TlsCipherSuiteID(0x1a1a)); // GREASE
        assert_eq!(hs.ciphersuites.len(), 0);
    }

    #[test]
    fn test_add_cipher_suite_accepts_normal() {
        let mut hs = HandshakeParams::new();
        hs.add_cipher_suite(TlsCipherSuiteID(0x1301));
        assert_eq!(hs.ciphersuites, &[TlsCipherSuiteID(0x1301)]);
    }

    #[test]
    fn test_add_cipher_suite_len_tracking() {
        let mut hs = HandshakeParams::new();
        hs.add_cipher_suite(TlsCipherSuiteID(0x1301));
        hs.add_cipher_suite(TlsCipherSuiteID(0x1302));
        hs.add_cipher_suite(TlsCipherSuiteID(0x1a1a)); // GREASE
        assert_eq!(hs.ciphersuites.len(), 2);
    }

    #[test]
    fn test_add_extension_sets_domain_for_server_name() {
        let mut hs = HandshakeParams::new();
        hs.add_extension(TlsExtensionType::ServerName);
        assert!(hs.domain);
    }

    #[test]
    fn test_add_extension_filters_grease() {
        let mut hs = HandshakeParams::new();
        hs.add_extension(TlsExtensionType(0xaaaa)); // GREASE
        assert_eq!(hs.extensions.len(), 0);
    }

    #[test]
    fn test_add_extension_len_tracking() {
        let mut hs = HandshakeParams::new();
        hs.add_extension(TlsExtensionType::ClientCertificate);
        hs.add_extension(TlsExtensionType::ServerName);
        hs.add_extension(TlsExtensionType(0xaaaa)); // GREASE
        assert_eq!(hs.extensions.len(), 2);
    }

    #[test]
    fn test_add_signature_algorithm_filters_grease() {
        let mut hs = HandshakeParams::new();
        hs.add_signature_algorithm(0xbaba); // GREASE
        assert_eq!(hs.signature_algorithms.len(), 0);
    }

    #[test]
    fn test_add_signature_algorithm_len_tracking() {
        let mut hs = HandshakeParams::new();
        hs.add_signature_algorithm(0x1234);
        hs.add_signature_algorithm(0x1235);
        hs.add_signature_algorithm(0xbaba); // GREASE
        assert_eq!(hs.signature_algorithms.len(), 2);
    }
}
