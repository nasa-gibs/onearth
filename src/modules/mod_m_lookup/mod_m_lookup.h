#if !defined(MOD_M_LOOKUP_H)

#include <lua.h>

// // The maximum file size that this module can handle
#define MAX_FILE_SIZE 1024*1024


typedef struct {
    ap_regex_t *regexp;
    char *filename;
    char *type;
} match;

typedef struct {
	const char *lookup_script;
	apr_size_t lookup_script_len;
	const char *endpoint;
	apr_array_header_t *regexp;
	ap_regex_t *lookup_service_regexp;
} m_lookup_conf;

extern module AP_MODULE_DECLARE_DATA m_lookup_module;

#endif
