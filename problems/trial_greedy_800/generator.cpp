#include "testlib.h"
#include <iostream>
#include <vector>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    
    int idx = atoi(argv[1]);
    int total = atoi(argv[2]);
    
    int n;
    long long maxVal;
    
    if (idx <= 3) {
        // 小数据：n 较小
        n = rnd.next(1, 5);
        maxVal = rnd.next(1, 10);
    } else if (idx <= 6) {
        // 中等数据
        n = rnd.next(5, 20);
        maxVal = rnd.next(1, 100);
    } else if (idx <= 10) {
        // 随机数据
        n = rnd.next(1, 100);
        maxVal = rnd.next(1, 10000);
    } else if (idx <= 15) {
        // 较大数据
        n = rnd.next(100, 500);
        maxVal = rnd.next(1, 100000);
    } else if (idx <= 19) {
        // 大数据
        n = rnd.next(500, 1000);
        maxVal = rnd.next(1, 1000000);
    } else {
        // 边界情况
        if (idx == 20) {
            // n = 1
            n = 1;
            maxVal = 1000000;
        } else if (idx == 21) {
            // n = 1000，全部相同
            n = 1000;
            maxVal = 1;
        } else if (idx == 22) {
            // n = 1000，已经严格递增
            n = 1000;
            maxVal = 1;
        } else if (idx == 23) {
            // n = 1000，严格递减
            n = 1000;
            maxVal = 1000000;
        } else {
            // n = 1000，随机大值
            n = 1000;
            maxVal = 1000000;
        }
    }
    
    cout << n << endl;
    
    if (idx == 22) {
        // 已经严格递增
        for (int i = 0; i < n; i++) {
            cout << (i + 1);
            if (i + 1 < n) cout << " ";
        }
    } else if (idx == 23) {
        // 严格递减
        for (int i = 0; i < n; i++) {
            cout << (n - i);
            if (i + 1 < n) cout << " ";
        }
    } else {
        // 随机生成
        for (int i = 0; i < n; i++) {
            cout << rnd.next(1LL, maxVal);
            if (i + 1 < n) cout << " ";
        }
    }
    cout << endl;
    
    return 0;
}
