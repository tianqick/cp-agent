#include "testlib.h"
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    
    int idx = atoi(argv[1]);
    int total = atoi(argv[2]);
    
    int n, k;
    long long d;
    
    if (idx == 1) {
        // 最小规模
        n = 1; k = 1; d = 0;
    } else if (idx == 2) {
        // n=1, k=1, d很大
        n = 1; k = 1; d = 1000000000;
    } else if (idx == 3) {
        // 所有人一组
        n = 5; k = 5; d = 0;
    } else if (idx == 4) {
        // 每人一组
        n = 5; k = 1; d = 100;
    } else if (idx == 5) {
        // d=0，相同分数
        n = 6; k = 3; d = 0;
    } else if (idx == 6) {
        // d很大，按k分组
        n = 10; k = 3; d = 1000000000;
    } else if (idx <= 15) {
        // 小规模
        n = rnd.next(2, 20);
        k = rnd.next(1, n);
        d = rnd.next(0LL, 1000000000LL);
    } else if (idx <= 25) {
        // 中等规模
        n = rnd.next(100, 1000);
        k = rnd.next(1, n);
        d = rnd.next(0LL, 1000000000LL);
    } else {
        // 大规模
        n = rnd.next(10000, 100000);
        k = rnd.next(1, n);
        d = rnd.next(0LL, 1000000000LL);
    }
    
    cout << n << " " << k << " " << d << endl;
    
    vector<long long> a(n);
    for (int i = 0; i < n; i++) {
        a[i] = rnd.next(1LL, 1000000000LL);
    }
    
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << a[i];
    }
    cout << endl;
    
    return 0;
}
