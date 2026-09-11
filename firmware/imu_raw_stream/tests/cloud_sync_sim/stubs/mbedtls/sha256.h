#pragma once
#include <stddef.h>
typedef struct { int x; } mbedtls_sha256_context;
void mbedtls_sha256_init(mbedtls_sha256_context*); void mbedtls_sha256_free(mbedtls_sha256_context*);
int mbedtls_sha256_starts_ret(mbedtls_sha256_context*, int is224);
int mbedtls_sha256_update_ret(mbedtls_sha256_context*, const unsigned char* input, size_t ilen);
int mbedtls_sha256_finish_ret(mbedtls_sha256_context*, unsigned char output[32]);
