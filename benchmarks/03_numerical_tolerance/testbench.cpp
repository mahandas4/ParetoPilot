#include <cmath>
void fill(float x[256]) { x[0] = 100000000.0f; for (int i=1;i<255;++i) x[i]=1.0f; x[255]=-100000000.0f; }
double kernel(const float in[256]);
int main() {
    float in[256]; fill(in);
    return std::fabs(kernel(in) - 254.0) <= 0.01 ? 0 : 1;
}
