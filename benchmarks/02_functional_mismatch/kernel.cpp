void kernel(const int a[64], const int b[64], int out[64]) {
    for (int i = 0; i < 64; ++i) {
        out[i] = a[i] - b[i];
    }
}
