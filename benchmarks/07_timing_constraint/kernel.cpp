float kernel(float x) {
#pragma HLS INLINE off
    float y=x;
    for(int i=0;i<32;++i) {
#pragma HLS UNROLL
        y=y*1.0001f+0.0003f;
    }
    return y;
}
