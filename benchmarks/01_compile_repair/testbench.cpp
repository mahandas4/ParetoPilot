#include <cstdlib>
void kernel(const int in[16], int out[16]);
int main() {
    int in[16], out[16];
    for (int i = 0; i < 16; ++i) in[i] = i - 7;
    kernel(in, out);
    for (int i = 0; i < 16; ++i) if (out[i] != in[i] + 1) return 1;
    return 0;
}
