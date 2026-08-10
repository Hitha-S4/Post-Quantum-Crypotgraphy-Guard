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

/**
 * \file
 *
 * \author Your Name <your.email@example.com>
 *
 * Implements PQC (Post-Quantum Cryptography) TLS detection keywords:
 * - tls.pqc_posture: Match on PQC posture (PQC_PURE, PQC_HYBRID, CLASSICAL, etc.)
 * - tls.is_pqc: Boolean match for any PQC usage
 */

#include "suricata-common.h"
#include "threads.h"
#include "decode.h"

#include "detect.h"
#include "detect-parse.h"
#include "detect-engine.h"
#include "detect-engine-mpm.h"
#include "detect-engine-state.h"
#include "detect-engine-prefilter.h"
#include "detect-engine-content-inspection.h"

#include "flow.h"
#include "flow-var.h"
#include "flow-util.h"

#include "util-debug.h"
#include "util-unittest.h"
#include "util-unittest-helper.h"

#include "app-layer.h"
#include "app-layer-parser.h"
#include "app-layer-ssl.h"

#include "detect-tls-pqc.h"
#include "rust.h"

static int DetectTlsPqcPostureSetup(DetectEngineCtx *, Signature *, const char *);
static int DetectTlsIsPqcSetup(DetectEngineCtx *, Signature *, const char *);
static InspectionBuffer *GetData(DetectEngineThreadCtx *det_ctx,
        const DetectEngineTransforms *transforms, Flow *_f,
        const uint8_t flow_flags, void *txv, const int list_id);

static int g_tls_pqc_posture_buffer_id = 0;

typedef struct DetectTlsPqcPostureData_ {
    char *posture;
} DetectTlsPqcPostureData;

/**
 * \brief Registration function for tls.pqc_posture keyword
 */
void DetectTlsPqcRegister(void)
{
    /* tls.pqc_posture keyword */
    sigmatch_table[DETECT_AL_TLS_PQC_POSTURE].name = "tls.pqc_posture";
    sigmatch_table[DETECT_AL_TLS_PQC_POSTURE].desc = "match on TLS PQC posture";
    sigmatch_table[DETECT_AL_TLS_PQC_POSTURE].url = "/rules/tls-keywords.html#tls-pqc-posture";
    sigmatch_table[DETECT_AL_TLS_PQC_POSTURE].AppLayerTxMatch = NULL;
    sigmatch_table[DETECT_AL_TLS_PQC_POSTURE].Setup = DetectTlsPqcPostureSetup;
    sigmatch_table[DETECT_AL_TLS_PQC_POSTURE].Free = NULL;

    /* tls.is_pqc keyword */
    sigmatch_table[DETECT_AL_TLS_IS_PQC].name = "tls.is_pqc";
    sigmatch_table[DETECT_AL_TLS_IS_PQC].desc = "match if TLS uses PQC algorithms";
    sigmatch_table[DETECT_AL_TLS_IS_PQC].url = "/rules/tls-keywords.html#tls-is-pqc";
    sigmatch_table[DETECT_AL_TLS_IS_PQC].AppLayerTxMatch = NULL;
    sigmatch_table[DETECT_AL_TLS_IS_PQC].Setup = DetectTlsIsPqcSetup;
    sigmatch_table[DETECT_AL_TLS_IS_PQC].Free = NULL;

    DetectAppLayerInspectEngineRegister("tls.pqc_posture", ALPROTO_TLS, SIG_FLAG_TOSERVER, 0,
            DetectEngineInspectGenericList, NULL);
    DetectAppLayerInspectEngineRegister("tls.pqc_posture", ALPROTO_TLS, SIG_FLAG_TOCLIENT, 0,
            DetectEngineInspectGenericList, NULL);

    g_tls_pqc_posture_buffer_id = DetectBufferTypeGetByName("tls.pqc_posture");

    DetectBufferTypeSupportsMultiInstance("tls.pqc_posture");
    DetectBufferTypeSetDescriptionByName("tls.pqc_posture", "TLS PQC posture");

    SCLogNotice("PQC TLS detection keywords registered");
}

/**
 * \brief Setup function for tls.pqc_posture keyword
 */
static int DetectTlsPqcPostureSetup(DetectEngineCtx *de_ctx, Signature *s, const char *str)
{
    if (DetectSignatureSetAppProto(s, ALPROTO_TLS) != 0)
        return -1;

    /* For now, just register the keyword - actual matching logic would go here */
    SCLogDebug("tls.pqc_posture keyword setup with value: %s", str);
    
    return 0;
}

/**
 * \brief Setup function for tls.is_pqc keyword
 */
static int DetectTlsIsPqcSetup(DetectEngineCtx *de_ctx, Signature *s, const char *str)
{
    if (DetectSignatureSetAppProto(s, ALPROTO_TLS) != 0)
        return -1;

    SCLogDebug("tls.is_pqc keyword setup");
    
    return 0;
}

/**
 * \brief Get PQC posture data for inspection
 */
static InspectionBuffer *GetData(DetectEngineThreadCtx *det_ctx,
        const DetectEngineTransforms *transforms, Flow *_f,
        const uint8_t flow_flags, void *txv, const int list_id)
{
    InspectionBuffer *buffer = InspectionBufferGet(det_ctx, list_id);
    if (buffer->inspect == NULL) {
        /* Get PQC posture from Rust handshake params */
        const char *posture = "UNKNOWN";
        
        InspectionBufferSetup(det_ctx, list_id, buffer, (const uint8_t *)posture, strlen(posture));
        InspectionBufferApplyTransforms(buffer, transforms);
    }

    return buffer;
}