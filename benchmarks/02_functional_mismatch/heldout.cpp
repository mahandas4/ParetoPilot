void kernel(const int a[64], const int b[64], int out[64]);
int main() {
    int a[64], b[64], out[64];
    for (int i = 0; i < 64; ++i) { a[i] = (i & 1) ? -i : i; b[i] = 101 - i; }
    kernel(a, b, out);
    for (int i = 0; i < 64; ++i) if (out[i] != a[i] + b[i]) return 1;
    return 0;
}
