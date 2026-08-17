void kernel(const int in[16], int out[16]) {
    for (int i = 0; i < 16; ++i) {
        out[i] = in[i] + bias;
    }
}
