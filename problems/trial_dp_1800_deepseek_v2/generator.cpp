#include "testlib.h"
#include <iostream>
#include <vector>
using namespace std;

typedef long long ll;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    int idx = atoi(argv[1]);
    int total = atoi(argv[2]);
    
    int n;
    ll minVal = -1000000000LL;
    ll maxVal = 1000000000LL;
    
    // If total is large, it's a stress test — keep n small for naive
    bool stressMode = (total >= 200);
    
    if (stressMode) {
        n = rnd.next(1, 15);
    } else if (total <= 5) {
        n = rnd.next(1, 6);
    } else if (idx <= total / 5) {
        n = rnd.next(1, 15);
    } else if (idx <= total * 2 / 5) {
        n = rnd.next(16, 500);
    } else if (idx <= total * 3 / 5) {
        n = rnd.next(501, 2000);
    } else {
        n = rnd.next(4000, 5000);
    }
    
    cout << n << endl;
    vector<ll> a(n);
    for (int i = 0; i < n; i++) {
        int strategy = rnd.next(1, 10);
        if (strategy <= 6) {
            a[i] = rnd.next(minVal, maxVal);
        } else if (strategy <= 8) {
            a[i] = rnd.next(-100, 100);
        } else {
            int bit = rnd.next(0, 29);
            a[i] = (1LL << bit);
            if (rnd.next(0, 1)) a[i] = -a[i];
        }
    }
    
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << a[i];
    }
    cout << endl;
    
    return 0;
}
