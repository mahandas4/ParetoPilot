#include <cmath>
double kernel(const float in[256]);
int main() {
    float in[256];
    for (int i=0;i<256;++i) in[i] = (i % 3 == 0) ? 0.1f : -0.025f;
    double reference=0.0; for (int i=0;i<256;++i) reference += (double)in[i];
    return std::fabs(kernel(in)-reference) <= 0.01 ? 0 : 1;
}
