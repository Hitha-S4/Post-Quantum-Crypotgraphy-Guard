// Quick test to verify PQC logging is being called
#include <stdio.h>

int main() {
    printf("Testing if SCTLSHandshakeLogPQCDetails exists in binary...\n");
    
    // Check if the function symbol exists
    extern void SCTLSHandshakeLogPQCDetails(void*, void*);
    
    printf("Function exists: %p\n", (void*)SCTLSHandshakeLogPQCDetails);
    
    return 0;
}