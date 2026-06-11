#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>
using namespace std;

typedef long long ll;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    vector<ll> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }
    
    // Brute force: enumerate all 2^(n-1) partitions
    // For n <= 15, this is at most 16384 partitions
    ll ans = LLONG_MIN;
    int ways = 1 << (n - 1);
    
    for (int mask = 0; mask < ways; mask++) {
        ll total = 0;
        ll curXor = 0;
        
        for (int i = 0; i < n; i++) {
            curXor ^= a[i];
            // If bit i is set (or i is last), end segment here
            if (i == n - 1 || (mask >> i) & 1) {
                total += curXor;
                curXor = 0;
            }
        }
        
        if (total > ans) ans = total;
    }
    
    cout << ans << '\n';
    
    return 0;
}
