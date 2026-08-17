void kernel(const int in[256], int out[256]) {
    for(int i=0;i<256;++i) out[i]=in[i]*3+7;
}
