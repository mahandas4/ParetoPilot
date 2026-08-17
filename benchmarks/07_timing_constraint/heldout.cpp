#include <cmath>
float kernel(float x);
static float ref(float x){for(int i=0;i<32;++i)x=x*1.0001f+0.0003f;return x;}
int main(){float x=3.14159f;return std::fabs(kernel(x)-ref(x))<=0.001f?0:1;}
