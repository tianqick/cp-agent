#include "testlib.h"
#include <iostream>
using namespace std;
using ll = long long;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    int idx = atoi(argv[1]);
    int total = atoi(argv[2]);

    int n;
    int maxVal = 1000000000;
    int minVal = -1000000000;

    bool stress = (total > 30); // stress test mode: keep n small

    if (stress) {
        n = rnd.next(1, 200);
    } else {
        // Formal test data: diverse sizes
        if (idx <= 3) {
            n = 1; // minimal corner cases
        } else if (idx <= 6) {
            n = rnd.next(2, 50); // small
        } else if (idx <= 10) {
            n = rnd.next(100, 1000); // medium
        } else if (idx <= 14) {
            n = rnd.next(10000, 50000); // large
        } else if (idx <= 18) {
            n = rnd.next(100000, 200000); // very large
        } else {
            n = 200000; // maximum
        }
    }

    cout << n << endl;
    vector<ll> a(n);

    if (!stress) {
        // Diverse patterns based on idx
        if (idx == 1) {
            // single positive
            cout << rnd.next(1, maxVal) << endl;
            return 0;
        }
        if (idx == 2) {
            // single negative
            cout << rnd.next(minVal, -1) << endl;
            return 0;
        }
        if (idx == 3) {
            // single zero
            cout << 0 << endl;
            return 0;
        }
    }

    if (idx % 7 == 1) {
        // all positive
        for (int i = 0; i < n; i++) a[i] = rnd.next(1, maxVal);
    } else if (idx % 7 == 2) {
        // all negative
        for (int i = 0; i < n; i++) a[i] = rnd.next(minVal, -1);
    } else if (idx % 7 == 3) {
        // alternating signs
        for (int i = 0; i < n; i++) {
            int sign = (i % 2 == 0) ? 1 : -1;
            a[i] = sign * rnd.next(1, 10000);
        }
    } else if (idx % 7 == 4) {
        // mostly positive with some negatives
        for (int i = 0; i < n; i++) {
            if (rnd.next(1, 100) <= 20)
                a[i] = rnd.next(minVal, -1);
            else
                a[i] = rnd.next(1, maxVal);
        }
    } else if (idx % 7 == 5) {
        // mostly negative with some positives
        for (int i = 0; i < n; i++) {
            if (rnd.next(1, 100) <= 20)
                a[i] = rnd.next(1, maxVal);
            else
                a[i] = rnd.next(minVal, -1);
        }
    } else if (idx % 7 == 6) {
        // random with large magnitude variation
        for (int i = 0; i < n; i++) {
            a[i] = rnd.next(minVal, maxVal);
        }
    } else {
        // fully random (idx % 7 == 0)
        for (int i = 0; i < n; i++) {
            a[i] = rnd.next(minVal, maxVal);
        }
    }

    for (int i = 0; i < n; i++) {
        cout << a[i];
        if (i + 1 < n) cout << " ";
    }
    cout << endl;

    return 0;
}
