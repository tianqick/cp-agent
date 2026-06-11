#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

typedef long long ll;

ll gcd(ll a, ll b) {
    a = abs(a);
    b = abs(b);
    if (a == 0) return b;
    if (b == 0) return a;
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, q;
    cin >> n >> q;
    
    vector<ll> a(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }
    
    while (q--) {
        int type;
        cin >> type;
        
        if (type == 1) {
            // 区间加法 [l, r] + x
            int l, r;
            ll x;
            cin >> l >> r >> x;
            
            for (int i = l; i <= r; i++) {
                a[i] += x;
            }
        } else {
            // 查询 [l, r] 的 GCD
            int l, r;
            cin >> l >> r;
            
            ll result = 0;
            for (int i = l; i <= r; i++) {
                result = gcd(result, a[i]);
            }
            cout << result << "\n";
        }
    }
    
    return 0;
}