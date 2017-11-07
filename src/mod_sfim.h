/*
* mod_sfim header file
* Lucian Plesea
* (C) 2016
*/

#if !defined(MOD_SFIM_H)

// The maximum file size that this module can handle
#define MAX_FILE_SIZE 1024*1024


typedef struct {
    ap_regex_t *regx;
    char *filename;
    char *type;
} match;

typedef struct {
    // An apr array is somewhat like a C++ vector
    apr_array_header_t *matches;
    // Callback regexp
    ap_regex_t *cbackregx;
} sfim_conf;

extern module AP_MODULE_DECLARE_DATA sfim_module;

#endif
