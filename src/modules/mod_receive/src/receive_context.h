//
// The context definition for the receive module
// On output size holds the received size
//
#if !defined(RECEIVE_CTX_H)
typedef struct {
    char *buffer;
    int size;
    int maxsize;
    int overflow;
} receive_ctx;
#endif
