#include <cmath>
float kernel(float x);
static float ref(float x){for(int i=0;i<32;++i)x=x*1.0001f+0.0003f;return x;}
int main(){for(int i=-4;i<=4;++i)if(std::fabs(kernel(i*0.25f)-ref(i*0.25f))>0.001f)return 1;return 0;}
