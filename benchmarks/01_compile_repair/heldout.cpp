void kernel(const int in[16], int out[16]);
int main() {
    int in[16] = {2147483000, -19, 0, 4}, out[16] = {};
    kernel(in, out);
    for (int i = 0; i < 16; ++i) if (out[i] != in[i] + 1) return 1;
    return 0;
}
