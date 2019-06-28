/*
 *
 * An AHTSE module that modifies PNG chunk information
 * Lucian Plesea
 * (C) 2019
 * 
 */

#include <ahtse.h>
#include <cctype>
#include <receive_context.h>
#include <http_request.h>
#include <http_protocol.h>
#include <http_log.h>

using namespace std;

NS_AHTSE_USE

extern module AP_MODULE_DECLARE_DATA ahtse_png_module;

#if defined(APLOG_USE_MODULE)
APLOG_USE_MODULE(ahtse_png);
#endif

// Colors, anonymous enum
enum { RED = 0, GREEN, BLUE, ALPHA, BANDS };
enum PG_TYPE { LUMA = 0, RGB = 2, PIDX = 3, LA = 4, RGBA = 6};

// PNG constants
static const apr_byte_t PNGSIG[8] = { 0x89, 0x50, 0x4e, 0x47, 
                                    0x0d, 0x0a, 0x1a, 0x0a };

static const apr_byte_t IHDR[4] = { 0x49, 0x48, 0x44, 0x52 };
static const apr_byte_t PLTE[4] = { 0x50, 0x4c, 0x54, 0x45 };
static const apr_byte_t tRNS[4] = { 0x74, 0x52, 0x4e, 0x53 };
static const apr_byte_t IDAT[4] = { 0x49, 0x44, 0x41, 0x54 };
static const apr_byte_t IEND[4] = { 0x49, 0x45, 0x4e, 0x44 };

// PNG chunk structrure is
//LEN + SIG + (DATA) + CHECKSUM
//LEN is length of DATA, 0 is valid
// Thus an empty chunk takes at least 12 bytes

// Compares 4 bytes
static int is_same_4(const apr_byte_t *s1, const apr_byte_t *s2) {
    return s1[0] == s2[0] && s1[1] == s2[1] && 
        s1[2] == s2[2] && s1[3] == s2[3];
}

// Compares 8 bytes
static int is_same_8(const apr_byte_t *s1, const apr_byte_t *s2) {
    return is_same_4(s1, s2) && is_same_4(s1 + 4, s2 + 4);
}

// PNG CRC implementation, slightly modified for C++ from zlib, single table
static apr_uint32_t update_crc32(unsigned char *buf, int len, 
    apr_uint32_t crc = 0xffffffff)
{
    static const apr_uint32_t table[256] = {
        0x00000000UL, 0x77073096UL, 0xee0e612cUL, 0x990951baUL, 0x076dc419UL,
        0x706af48fUL, 0xe963a535UL, 0x9e6495a3UL, 0x0edb8832UL, 0x79dcb8a4UL,
        0xe0d5e91eUL, 0x97d2d988UL, 0x09b64c2bUL, 0x7eb17cbdUL, 0xe7b82d07UL,
        0x90bf1d91UL, 0x1db71064UL, 0x6ab020f2UL, 0xf3b97148UL, 0x84be41deUL,
        0x1adad47dUL, 0x6ddde4ebUL, 0xf4d4b551UL, 0x83d385c7UL, 0x136c9856UL,
        0x646ba8c0UL, 0xfd62f97aUL, 0x8a65c9ecUL, 0x14015c4fUL, 0x63066cd9UL,
        0xfa0f3d63UL, 0x8d080df5UL, 0x3b6e20c8UL, 0x4c69105eUL, 0xd56041e4UL,
        0xa2677172UL, 0x3c03e4d1UL, 0x4b04d447UL, 0xd20d85fdUL, 0xa50ab56bUL,
        0x35b5a8faUL, 0x42b2986cUL, 0xdbbbc9d6UL, 0xacbcf940UL, 0x32d86ce3UL,
        0x45df5c75UL, 0xdcd60dcfUL, 0xabd13d59UL, 0x26d930acUL, 0x51de003aUL,
        0xc8d75180UL, 0xbfd06116UL, 0x21b4f4b5UL, 0x56b3c423UL, 0xcfba9599UL,
        0xb8bda50fUL, 0x2802b89eUL, 0x5f058808UL, 0xc60cd9b2UL, 0xb10be924UL,
        0x2f6f7c87UL, 0x58684c11UL, 0xc1611dabUL, 0xb6662d3dUL, 0x76dc4190UL,
        0x01db7106UL, 0x98d220bcUL, 0xefd5102aUL, 0x71b18589UL, 0x06b6b51fUL,
        0x9fbfe4a5UL, 0xe8b8d433UL, 0x7807c9a2UL, 0x0f00f934UL, 0x9609a88eUL,
        0xe10e9818UL, 0x7f6a0dbbUL, 0x086d3d2dUL, 0x91646c97UL, 0xe6635c01UL,
        0x6b6b51f4UL, 0x1c6c6162UL, 0x856530d8UL, 0xf262004eUL, 0x6c0695edUL,
        0x1b01a57bUL, 0x8208f4c1UL, 0xf50fc457UL, 0x65b0d9c6UL, 0x12b7e950UL,
        0x8bbeb8eaUL, 0xfcb9887cUL, 0x62dd1ddfUL, 0x15da2d49UL, 0x8cd37cf3UL,
        0xfbd44c65UL, 0x4db26158UL, 0x3ab551ceUL, 0xa3bc0074UL, 0xd4bb30e2UL,
        0x4adfa541UL, 0x3dd895d7UL, 0xa4d1c46dUL, 0xd3d6f4fbUL, 0x4369e96aUL,
        0x346ed9fcUL, 0xad678846UL, 0xda60b8d0UL, 0x44042d73UL, 0x33031de5UL,
        0xaa0a4c5fUL, 0xdd0d7cc9UL, 0x5005713cUL, 0x270241aaUL, 0xbe0b1010UL,
        0xc90c2086UL, 0x5768b525UL, 0x206f85b3UL, 0xb966d409UL, 0xce61e49fUL,
        0x5edef90eUL, 0x29d9c998UL, 0xb0d09822UL, 0xc7d7a8b4UL, 0x59b33d17UL,
        0x2eb40d81UL, 0xb7bd5c3bUL, 0xc0ba6cadUL, 0xedb88320UL, 0x9abfb3b6UL,
        0x03b6e20cUL, 0x74b1d29aUL, 0xead54739UL, 0x9dd277afUL, 0x04db2615UL,
        0x73dc1683UL, 0xe3630b12UL, 0x94643b84UL, 0x0d6d6a3eUL, 0x7a6a5aa8UL,
        0xe40ecf0bUL, 0x9309ff9dUL, 0x0a00ae27UL, 0x7d079eb1UL, 0xf00f9344UL,
        0x8708a3d2UL, 0x1e01f268UL, 0x6906c2feUL, 0xf762575dUL, 0x806567cbUL,
        0x196c3671UL, 0x6e6b06e7UL, 0xfed41b76UL, 0x89d32be0UL, 0x10da7a5aUL,
        0x67dd4accUL, 0xf9b9df6fUL, 0x8ebeeff9UL, 0x17b7be43UL, 0x60b08ed5UL,
        0xd6d6a3e8UL, 0xa1d1937eUL, 0x38d8c2c4UL, 0x4fdff252UL, 0xd1bb67f1UL,
        0xa6bc5767UL, 0x3fb506ddUL, 0x48b2364bUL, 0xd80d2bdaUL, 0xaf0a1b4cUL,
        0x36034af6UL, 0x41047a60UL, 0xdf60efc3UL, 0xa867df55UL, 0x316e8eefUL,
        0x4669be79UL, 0xcb61b38cUL, 0xbc66831aUL, 0x256fd2a0UL, 0x5268e236UL,
        0xcc0c7795UL, 0xbb0b4703UL, 0x220216b9UL, 0x5505262fUL, 0xc5ba3bbeUL,
        0xb2bd0b28UL, 0x2bb45a92UL, 0x5cb36a04UL, 0xc2d7ffa7UL, 0xb5d0cf31UL,
        0x2cd99e8bUL, 0x5bdeae1dUL, 0x9b64c2b0UL, 0xec63f226UL, 0x756aa39cUL,
        0x026d930aUL, 0x9c0906a9UL, 0xeb0e363fUL, 0x72076785UL, 0x05005713UL,
        0x95bf4a82UL, 0xe2b87a14UL, 0x7bb12baeUL, 0x0cb61b38UL, 0x92d28e9bUL,
        0xe5d5be0dUL, 0x7cdcefb7UL, 0x0bdbdf21UL, 0x86d3d2d4UL, 0xf1d4e242UL,
        0x68ddb3f8UL, 0x1fda836eUL, 0x81be16cdUL, 0xf6b9265bUL, 0x6fb077e1UL,
        0x18b74777UL, 0x88085ae6UL, 0xff0f6a70UL, 0x66063bcaUL, 0x11010b5cUL,
        0x8f659effUL, 0xf862ae69UL, 0x616bffd3UL, 0x166ccf45UL, 0xa00ae278UL,
        0xd70dd2eeUL, 0x4e048354UL, 0x3903b3c2UL, 0xa7672661UL, 0xd06016f7UL,
        0x4969474dUL, 0x3e6e77dbUL, 0xaed16a4aUL, 0xd9d65adcUL, 0x40df0b66UL,
        0x37d83bf0UL, 0xa9bcae53UL, 0xdebb9ec5UL, 0x47b2cf7fUL, 0x30b5ffe9UL,
        0xbdbdf21cUL, 0xcabac28aUL, 0x53b39330UL, 0x24b4a3a6UL, 0xbad03605UL,
        0xcdd70693UL, 0x54de5729UL, 0x23d967bfUL, 0xb3667a2eUL, 0xc4614ab8UL,
        0x5d681b02UL, 0x2a6f2b94UL, 0xb40bbe37UL, 0xc30c8ea1UL, 0x5a05df1bUL,
        0x2d02ef8dUL
    };

    apr_uint32_t val = crc;
    for (int n = 0; n < len; n++)
        val = table[(val ^ *buf++) & 0xff] ^ (val >> 8);
    return val;
}

static const int MIN_C_LEN = 12;

// The transmitted value is 1's complement
static apr_uint32_t crc32(unsigned char *buf, int len)
{
    return update_crc32(buf, len) ^ 0xffffffff;
}

// PNG values are always big endian
static void poke_u32be(apr_byte_t *dst, apr_uint32_t val) {
    dst[0] = static_cast<apr_byte_t>((val >> 24) & 0xff);
    dst[1] = static_cast<apr_byte_t>((val >> 16) & 0xff);
    dst[2] = static_cast<apr_byte_t>((val >> 8) & 0xff);
    dst[3] = static_cast<apr_byte_t>(val & 0xff);
}

static apr_uint32_t peek_u32be(const apr_byte_t *src) {
    return
        (static_cast<apr_uint32_t>(src[0]) << 24) +
        (static_cast<apr_uint32_t>(src[1]) << 16) +
        (static_cast<apr_uint32_t>(src[2]) << 8) +
        (static_cast<apr_uint32_t>(src[3]));
}

static apr_uint32_t chunk_len(const apr_byte_t *chunk) {
    return 12 + peek_u32be(chunk);
}

static bool is_chunk(const apr_byte_t *HSIG, void *buff) {
    return is_same_4(HSIG, reinterpret_cast<apr_byte_t *>(buff) + 4);
}

// Find the n-th PNG chunk with a specific signature
// assumes the file signature was already checked
// return null on failure

static apr_byte_t *find_chunk(const apr_byte_t *HSIG, 
    storage_manager &mgr, int occurence = 1)
{
    int off = 8; // How far we got
    apr_byte_t *p = reinterpret_cast<apr_byte_t *>(mgr.buffer); // First chunk
    while (off + MIN_C_LEN <= mgr.size) { // Need at least LEN + SIG + CHECKSUM
        apr_byte_t *chunk = p + off;
        if (is_chunk(HSIG, chunk) && (0 == --occurence))
            return chunk; // Found it
        // Skip this chunk
        off += MIN_C_LEN + peek_u32be(chunk);
    }
    return nullptr;
}

static apr_byte_t *next_chunk(apr_byte_t *chunk) {
    if (is_chunk(IEND, chunk))
        return nullptr; // No chunk past the end one
    apr_uint32_t len = peek_u32be(chunk);
    return chunk + 12 + len;
}

struct png_conf {
    apr_array_header_t *arr_rxp;
    // Raster Configuration, mostly ignored
    TiledRaster raster;
    int indirect;        // Subrequests only
    int only;            // Block non-pngs
    char *source;        // source path
    char *postfix;       // optional postfix
    apr_byte_t *chunk_PLTE;    // the PLTE chunk
    apr_byte_t *chunk_tRNS;    // the tRNS chunk
};

static void *create_dir_config(apr_pool_t *p, char *dummy) {
    png_conf *c = reinterpret_cast<png_conf *>(
        apr_pcalloc(p, sizeof(png_conf)));
    return c;
}

static const char *set_regexp(cmd_parms *cmd, png_conf *c, const char *pattern)
{
    return add_regexp_to_array(cmd->pool, &c->arr_rxp, pattern);
}

// Parses a byte value, returns the value and advances the *src,
// Sets *src to null on error
static apr_byte_t scan_byte(char **src, int base = 0) {
    char *entry = *src;
    while (isspace(*entry))
        entry++;

    if (isdigit(*entry)) {
        apr_int64_t val = apr_strtoi64(entry, &entry, base);
        if (!errno && val >= 0 && val <= 0xff) {
            *src = entry;
            return static_cast<apr_byte_t>(val);
        }
    }
    // Report an error by setting the src to nullptr
    *src = nullptr;
    return 0;
}

// Entries should be in the order of index values
// v should be a 256 * 4 byte array
// Index 0 defaults to 0 0 0 0
static const char *raw_palette(apr_array_header_t *entries, apr_byte_t *v, int *len)
{
    int ix = 0; // previous index
    for (int i = 0; i < entries->nelts; i++) {
        char *entry = APR_ARRAY_IDX(entries, i, char *);
        // An entry is: Index Red Green Blue Alpha, white space separated
        int idx = 4 * scan_byte(&entry);
        if (!entry)
            return "Invalid entry format";
        if (idx <= ix && !(ix == 0 && idx == 0))
            return "Entries have to be sorted by index value";
        for (int c = RED; c < BANDS; c++) {
            v[idx + c] = scan_byte(&entry);
            if (!entry) {
                if (ALPHA != c)
                    return "Entry parsing error, "
                    "should be at least 4 space separated byte values";
                v[idx + ALPHA] = 0xff;
            }
        }

        for (int j = ix + 4; j < idx; j += 4) { // Interpolate
            double fraction = static_cast<double>(j - ix) / (idx - ix);
            for (int c = RED; c < BANDS; c++)
                v[j + c] = static_cast<apr_byte_t>(0.5 + v[ix + c] 
                    + fraction * (v[idx + c] - v[ix + c]));
        }
        ix = idx;
    }
    *len = ix / 4 + 1;
    return nullptr;
}

// returns the number of entries in the tRNS
static int tRNSlen(const apr_byte_t *arr, int len) {
    while (len && 0xff == arr[(len - 1) * BANDS + ALPHA])
        len--;
    return len;
}

static apr_uint32_t get_crc(apr_byte_t *chunk) {
    apr_uint32_t len = peek_u32be(chunk);
    return peek_u32be(chunk + len + 8); // Last 4 bytes
}

static const char *configure(cmd_parms *cmd, png_conf *c, const char *fname)
{
    const char *err_message, *line;
    auto kvp = readAHTSEConfig(cmd->temp_pool, fname, &err_message);
    if (!kvp)
        return err_message;

    err_message = configRaster(cmd->pool, kvp, c->raster);
    if (err_message)
        return err_message;

    line = apr_table_get(kvp, "Palette");
    if (line) {     // Build precomputed PNG PLTE and tRNS chunks
        line = apr_table_getm(cmd->temp_pool, kvp, "Entry");
        if (!line)
            return "Palette requires at least one Entry";
        auto entries = tokenize(cmd->temp_pool, line, ',');
        if (entries->nelts > 256)
            return "Maximum number of entries is 256";
        auto arr = reinterpret_cast<apr_byte_t *>(
            apr_pcalloc(cmd->temp_pool, 256 * BANDS));
        int len = 0;
        err_message = raw_palette(entries, arr, &len);
        if (err_message)
            return err_message;

        // build PLTE chunk
        auto chunk = reinterpret_cast<apr_byte_t *>(
            apr_pcalloc(cmd->pool, 3 * len + MIN_C_LEN));
        poke_u32be(chunk, 3 * len);
        poke_u32be(chunk + 4, peek_u32be(PLTE));
        apr_byte_t *p = chunk + 8;
        for (int i = 0; i < len * BANDS; i += BANDS)
            for (int c = RED; c < ALPHA; c++) 
                *p++ = arr[i + c];
        poke_u32be(chunk + 8 + 3 * len,
            crc32(chunk + 4, 4 + 3 * len));
        c->chunk_PLTE = chunk;

        // Same for the tRNS, if needed
        int tlen = tRNSlen(arr, len);
        if (tlen) {
            chunk = reinterpret_cast<apr_byte_t *>(
                apr_pcalloc(cmd->pool, tlen + 12));
            poke_u32be(chunk, tlen);
            poke_u32be(chunk + 4, peek_u32be(tRNS));
            apr_byte_t *p = chunk + 8;
            for (int i = 0; i < tlen; i++)
                *p++ = arr[i * BANDS + ALPHA];
            poke_u32be(chunk + 8 + tlen,
                crc32(chunk + 4, 4 + tlen));
            c->chunk_tRNS = chunk;
        }
    } // Build PLTE and tRNS chunks

    // If we have a missing file but no ETAg, use the palette chunk sig
    if (c->raster.missing.data.buffer && c->raster.missing.eTag[0] == 0 && c->chunk_PLTE) {
        c->raster.seed = get_crc(c->chunk_PLTE);
        c->raster.seed *= (c->chunk_tRNS) ? get_crc(c->chunk_tRNS) : 0xb1e2473a; // mix the bits
        tobase32(c->raster.seed, c->raster.missing.eTag, 1);
    }

    return nullptr;
}

// Tile address should already be adjusted for skipped levels, 
// and within source raster bounds
// returns success or remote code
static int get_tile(request_rec *r, const char *remote, sloc_t tile,
    storage_manager &dst, char **psETag = NULL, const char * postfix = NULL)
{
    ap_filter_rec_t *receive_filter = ap_get_output_filter_handle("Receive");
    if (!receive_filter) {
        ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r,
            "Can't find receive filter, did you load mod_receive?");
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    receive_ctx rctx;
    rctx.buffer = dst.buffer;
    rctx.maxsize = dst.size;
    rctx.size = 0;
    char *stile = apr_psprintf(r->pool, "/%d/%d/%d/%d",
        static_cast<int>(tile.z),
        static_cast<int>(tile.l),
        static_cast<int>(tile.y),
        static_cast<int>(tile.x));

    if (stile[1] == '0') // Don't send the M if zero
        stile += 2;

    char *sub_uri = apr_pstrcat(r->pool, remote, "/tile", stile, postfix, NULL);
    request_rec *sr = ap_sub_req_lookup_uri(sub_uri, r, r->output_filters);
    ap_filter_t *rf = ap_add_output_filter_handle(receive_filter, &rctx, sr, sr->connection);
    int code = ap_run_sub_req(sr); // returns call status
    ap_remove_output_filter(rf);

    int status = sr->status;       // http code
    dst.size = rctx.size;

    const char *sETag = apr_table_get(sr->headers_out, "ETag");

    if (psETag && sETag)
        *psETag = apr_pstrdup(r->pool, sETag);

    ap_destroy_sub_req(sr);

    if (code == APR_SUCCESS && status == HTTP_OK)
        return APR_SUCCESS;

    ap_log_rerror(APLOG_MARK, APLOG_NOTICE, 0, r, "%s failed, %d", sub_uri, status);
    return status;
}

static int handler(request_rec *r) {
    if (r->method_number != M_GET)
        return DECLINED;

    png_conf *cfg = get_conf<png_conf>(r, &ahtse_png_module);
    if ((cfg->indirect && !r->main)
        || !requestMatches(r, cfg->arr_rxp))
        return DECLINED;

    // Our request
    sz tile;
    if (APR_SUCCESS != getMLRC(r, tile))
        return HTTP_BAD_REQUEST;

    char *sETag = NULL;
    storage_manager tilebuf;
    tilebuf.size = cfg->raster.maxtilesize;
    tilebuf.buffer = static_cast<char *>(apr_palloc(r->pool, tilebuf.size));
    if (!tilebuf.buffer) {
        ap_log_rerror(APLOG_MARK, APLOG_CRIT, 0, r, "Out of memory");
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    int code = get_tile(r, cfg->source, tile, tilebuf, &sETag);
    if (APR_SUCCESS != code)
        return code;

    // SIG + IHDR + IDAT + data + IEND == 58
    const static int MIN_PNG_SZ = 8 + 25 + 12 + 1 + 12;
    if (tilebuf.size < MIN_PNG_SZ) {
        ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "Input data too small %s", r->uri);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    // Got the tile, first check or build the ETag
    int is_empty;
    apr_uint64_t nETag = base32decode(sETag, &is_empty);
    if (is_empty)
        return sendEmptyTile(r, cfg->raster.missing);

    char ETag[16]; // Outgoing ETag
    tobase32(cfg->raster.seed ^ nETag, ETag);
    if (etagMatches(r, ETag)) {
        apr_table_set(r->headers_out, "ETag", ETag);
        return HTTP_NOT_MODIFIED;
    }

    if (!is_same_8(reinterpret_cast<apr_byte_t *>(tilebuf.buffer), PNGSIG)) {
        if (!cfg->only)
            return sendImage(r, tilebuf);
        else
            return sendEmptyTile(r, cfg->raster.missing);
    }

    // If is PNG, is it the right kind ?
    apr_byte_t *pIHDR = find_chunk(IHDR, tilebuf);
    if (!pIHDR || pIHDR != reinterpret_cast<apr_byte_t *>(tilebuf.buffer + 8)) {  // Borken PNG?
        ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "Input PNG is corrupt %s", r->uri);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    apr_uint32_t len = peek_u32be(pIHDR);
    if (len != 13) {
        ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "Bogus IHDR chunk, from %s", r->uri);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    //else { // Check the sum
    //    apr_uint32_t oldsum = peek_u32be(pIHDR + 8 + len);
    //    apr_uint32_t newsum = crc32(reinterpret_cast<unsigned char *>(pIHDR) + 4, len + 4);
    //    oldsum -= newsum;
    //}

    // Offset of PNG color type
    const int IHDR_ctype = 8 + 9;
    PG_TYPE ctype = PG_TYPE(pIHDR[IHDR_ctype]);

    // Figure out the size, adjust existing chunks
    int outlen = tilebuf.size;
    apr_byte_t *chunk = nullptr;

    // Subtractions
    if (cfg->chunk_PLTE && (ctype == LUMA || ctype == PIDX)) { // palette replacement or removal
        chunk = find_chunk(PLTE, tilebuf);
        if (chunk)
            outlen -= chunk_len(chunk);
        chunk = find_chunk(tRNS, tilebuf); // Remove the old chunk too
        if (chunk)
            outlen -= chunk_len(chunk);
    }

    // Additions
    // if size of chunk_PLTE is 0, no PLTE chunk is emitted
    bool send_PLTE = false;
    bool changed_IHDR = false;
    if (cfg->chunk_PLTE) {
        len = chunk_len(cfg->chunk_PLTE);
        if (len > MIN_C_LEN) {
            if (ctype == LUMA) { // Was grayscale
                ctype = PIDX; // Force palette
                chunk = find_chunk(IHDR, tilebuf);
                chunk[IHDR_ctype] = ctype;
                changed_IHDR = true;
            }

            if (ctype == PIDX) {
                send_PLTE = true;
                outlen += len;
            }
        }
        else { // Removing the existing palette, becomes grayscale
            if (ctype == PIDX) {
                ctype = LUMA;
                chunk = find_chunk(IHDR, tilebuf);
                chunk[IHDR_ctype] = ctype;
                changed_IHDR = true;
            }
        }
    }

    bool send_tRNS = false;
    if (cfg->chunk_tRNS) {
        len = chunk_len(cfg->chunk_tRNS);
        // Don't care about the type, assume tRNS is the right format
        if (len > MIN_C_LEN) {
            outlen += len;
            send_tRNS = true;
        }
    }

    // Redo the checksums of modified chunks
    if (changed_IHDR) {
        chunk = find_chunk(IHDR, tilebuf);
        len = chunk_len(chunk) - MIN_C_LEN;
        poke_u32be(chunk + len + 8, crc32(chunk + 4, len + 4));
    }

    apr_table_set(r->headers_out, "ETag", ETag);

    // The two paths defined by this variable should be the same, 
    // but for some reason using ap_rwrite multiple times (chunked)
    // seems to stall, at least under the windows debugger, except if extra sleep is added in the send chunk
    // loop
    bool use_outbuf = true;
    // Not sure why it stalls when called the wrong way, maybe because it's from different pools
    storage_manager outbuf;
    outbuf.size = outlen;
    outbuf.buffer = reinterpret_cast<char *>(apr_palloc(r->pool, outlen));

    // Got the size right, set it
    if (use_outbuf) {
        memcpy(outbuf.buffer, tilebuf.buffer, 8);
        outbuf.size = 8;
    }
    else {
        ap_set_content_type(r, "image/png");
        ap_set_content_length(r, static_cast<apr_off_t>(outlen));
        // Send out the chunks, in the proper order
        ap_rwrite(tilebuf.buffer, 8, r);
    }
    len = 8;

    chunk = reinterpret_cast<apr_byte_t *>(tilebuf.buffer) + 8;


    bool seen_IDAT = false;

    while(chunk) {
        // remove or replace the palette and tRNS
        if (cfg->chunk_PLTE && is_chunk(PLTE, chunk))
            continue;         
        if (cfg->chunk_tRNS && is_chunk(tRNS, chunk))
            continue;

        if ((!seen_IDAT) && is_chunk(IDAT, chunk)) {
            // Send stuf f that goes before IDAT, in the proper order

            if (use_outbuf) {
                if (send_PLTE) {
                    memcpy(outbuf.buffer + outbuf.size, cfg->chunk_PLTE, chunk_len(cfg->chunk_PLTE));
                    outbuf.size += chunk_len(cfg->chunk_PLTE);
                }
                if (send_tRNS) {
                    memcpy(outbuf.buffer + outbuf.size, cfg->chunk_tRNS, chunk_len(cfg->chunk_tRNS));
                    outbuf.size += chunk_len(cfg->chunk_tRNS);
                }
            }
            else {
                if (send_PLTE)
                    ap_rwrite(cfg->chunk_PLTE, chunk_len(cfg->chunk_PLTE), r);
                if (send_tRNS)
                    ap_rwrite(cfg->chunk_tRNS, chunk_len(cfg->chunk_tRNS), r);
            }

            seen_IDAT = true;
        }
        len += chunk_len(chunk);
        if (use_outbuf) {
            memcpy(outbuf.buffer + outbuf.size, chunk, chunk_len(chunk));
            outbuf.size += chunk_len(chunk);
        }
        else {
            ap_rwrite(chunk, chunk_len(chunk), r);
        }
        chunk = next_chunk(chunk);
    }

    if (use_outbuf)
        return sendImage(r, outbuf);

//    ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "Sent Modified PNG");
    return OK;
}

static void register_hooks(apr_pool_t *p) {
    ap_hook_handler(handler, NULL, NULL, APR_HOOK_LAST);
}

static const command_rec cmds[] = {
    AP_INIT_TAKE1(
        "AHTSE_PNG_RegExp",
        (cmd_func) set_regexp,
        0, // self pass arg, added to the config address
        ACCESS_CONF,
        "The request pattern the URI has to match"
    )

    ,AP_INIT_TAKE12(
        "AHTSE_PNG_Source",
        (cmd_func) set_source<png_conf>,
        0,
        ACCESS_CONF,
        "Required, internal path for the source. "
        "Optional postfix is space separated"
    )

    ,AP_INIT_FLAG(
        "AHTSE_PNG_Indirect",
        (cmd_func) ap_set_flag_slot,
        (void *)APR_OFFSETOF(png_conf, indirect),
        ACCESS_CONF, // availability
        "If set, module only activates on subrequests"
    )

    ,AP_INIT_TAKE1(
        "AHTSE_PNG_ConfigurationFile",
        (cmd_func) configure,
        0,
        ACCESS_CONF,
        "File holding the AHTSE_PNG configuration"
    )

    ,AP_INIT_FLAG(
        "AHTSE_PNG_Only",
        (cmd_func) ap_set_flag_slot,
        (void *)APR_OFFSETOF(png_conf, only),
        ACCESS_CONF, // availability
        "If set, non-png files are blocked and reported as warnings. "
        "Default is off, allowing them to be sent"
    )

    ,{NULL}
};

module AP_MODULE_DECLARE_DATA ahtse_png_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config,
    0,  // merge_dir_config
    0,  // create_server_config
    0,  // merge_server_config
    cmds,
    register_hooks
};
