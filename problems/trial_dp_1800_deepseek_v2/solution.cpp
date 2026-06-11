#include <iostream>
#include <vector>
#include <algorithm>
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
    
    // pref[i] = a[0] ^ a[1] ^ ... ^ a[i-1], pref[0] = 0
    vector<ll> pref(n + 1, 0);
    for (int i = 0; i < n; i++) {
        pref[i + 1] = pref[i] ^ a[i];
    }
    
    // dp[i] = max score for prefix of length i
    vector<ll> dp(n + 1, -1e18);
    dp[0] = 0;
    
    for (int i = 1; i <= n; i++) {
        ll best = -1e18;
        for (int j = 0; j < i; j++) {
            ll val = dp[j] + (pref[i] ^ pref[j]);
            if (val > best) best = val;
        }
        dp[i] = best;
    }
    
    cout << dp[n] << '\n';
    
    return 0;
}
