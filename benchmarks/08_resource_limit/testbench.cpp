#include <cmath>
void kernel(const float a[32],const float b[32],float out[32]);
int main(){float a[32],b[32],o[32];for(int i=0;i<32;++i){a[i]=i*0.5f;b[i]=3-i*0.02f;}kernel(a,b,o);for(int i=0;i<32;++i)if(std::fabs(o[i]-a[i]*b[i])>1e-5f)return 1;return 0;}
