#include "testlib.h"
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

typedef long long ll;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    
    int idx = atoi(argv[1]);
    int total = atoi(argv[2]);
    
    int n, q;
    
    // 根据total参数判断模式
    // stress_test通常使用小的total值（如1000）
    // 正式测试数据使用大的total值（如25）
    if (total >= 100) {
        // 对拍模式，使用小数据
        n = rnd.next(2, 10);
        q = rnd.next(2, 15);
    } else if (idx <= 5) {
        // 小数据
        n = rnd.next(1, 20);
        q = rnd.next(1, 20);
    } else if (idx <= 10) {
        // 中等数据
        n = rnd.next(100, 1000);
        q = rnd.next(100, 1000);
    } else if (idx <= 15) {
        // 大数据，多查询
        n = rnd.next(10000, 50000);
        q = rnd.next(10000, 50000);
    } else {
        // 最大数据
        n = rnd.next(100000, 200000);
        q = rnd.next(100000, 200000);
    }
    
    cout << n << " " << q << "\n";
    
    // 生成数组 a[i]
    for (int i = 0; i < n; i++) {
        ll val = rnd.next(1LL, 1000000000000LL);
        cout << val;
        if (i + 1 < n) cout << " ";
    }
    cout << "\n";
    
    // 生成查询
    for (int i = 0; i < q; i++) {
        int type = rnd.next(1, 2);
        cout << type << " ";
        
        int l = rnd.next(1, n);
        int r = rnd.next(l, n);
        cout << l << " " << r;
        
        if (type == 1) {
            // 区间加法，x 可以是负数
            ll x = rnd.next(-1000000LL, 1000000LL);
            cout << " " << x;
        }
        cout << "\n";
    }
    
    return 0;
}