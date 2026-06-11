#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;
using ll = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<ll> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    vector<ll> pref(n + 1, 0);
    for (int i = 0; i < n; i++) pref[i + 1] = pref[i] + a[i];

    vector<ll> dp(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        dp[i] = dp[i - 1]; // don't end segment here
        for (int j = 0; j < i; j++) {
            ll sum = pref[i] - pref[j];
            if (sum > 0) {
                dp[i] = max(dp[i], dp[j] + sum);
            }
        }
    }

    cout << dp[n] << '\n';
    return 0;
}
