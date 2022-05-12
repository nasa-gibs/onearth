/*
 * Filter that receives the response and returns, to be used from sub-requests
 * Lucian Plesea
 * (C) 2015-2016
 */

//
// mod_receive.cpp : A receive filter, to capture subrequest content
//

#include "mod_receive.h"

static apr_status_t filter_func(ap_filter_t* f, apr_bucket_brigade* bb)
{
    request_rec *r = f->r;
    receive_ctx *context = (receive_ctx *)f->ctx;
    LOG(f->r, "Receive context at %pm, size %d", context->buffer, context->size);

    if (NULL == context) { // Allocate context if it doesn't exist already
	context = (receive_ctx *) apr_palloc(r->pool, sizeof(receive_ctx));
	context->maxsize = START_BUF_SZ;
	context->buffer = (char *)apr_palloc(r->pool, context->maxsize);
	context->size = 0;
        context->overflow = 0;
    }
    
    // For each bucket
    for (apr_bucket *b = APR_BRIGADE_FIRST(bb);
	b != APR_BRIGADE_SENTINEL(bb);
	b = APR_BUCKET_NEXT(b))
    {
	// Ignore everything but the data
	if (APR_BUCKET_IS_EOS(b) || APR_BUCKET_IS_METADATA(b))
	    continue;

	apr_size_t bytes;
	const char *buf;
	if (APR_SUCCESS != apr_bucket_read(b, &buf, &bytes, APR_BLOCK_READ)) {
	    // Not sure what to do if reading fails
	    continue;
	}

	// Adjust the byte count to the available space
        if (context->maxsize - context->size < (int)bytes) {
            context->overflow += static_cast<int>(bytes - context->maxsize + context->size);
            bytes = static_cast<apr_size_t>(context->maxsize) - context->size;
        }

        if (0 != bytes) {
            memcpy(context->buffer + context->size, buf, bytes);
            context->size += static_cast<int>(bytes);
        }
    }

    // If the context was new use a note to pass back the location
    if (NULL == f->ctx) 
        apr_table_setn(r->notes, "Receive_context", (const char *)context);

    return APR_SUCCESS;
}

// No hooks, just register the receive filter
static void register_filter(apr_pool_t *p)

{
    ap_register_output_filter_protocol("Receive",
	filter_func,
	NULL,
	AP_FTYPE_CONTENT_SET,
	AP_FILTER_PROTO_CHANGE | AP_FILTER_PROTO_CHANGE_LENGTH
	);
}

module AP_MODULE_DECLARE_DATA receive_module = {
    STANDARD20_MODULE_STUFF,
    0, 0, 0, 0, 0, register_filter
};
