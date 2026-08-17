void kernel(const float a[32], const float b[32], float out[32]) {
    for(int i=0;i<32;++i) {
#pragma HLS UNROLL
        out[i]=a[i]*b[i];
    }
}
