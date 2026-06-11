#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;
using ll = long long;

const ll INF = 1e18;

struct BIT {
    int n;
    vector<ll> tree;
    BIT(int n) : n(n), tree(n + 2, -INF) {}
    void update(int idx, ll val) {
        for (; idx <= n; idx += idx & -idx)
            if (val > tree[idx]) tree[idx] = val;
    }
    ll query(int idx) {
        ll res = -INF;
        for (; idx > 0; idx -= idx & -idx)
            if (tree[idx] > res) res = tree[idx];
        return res;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<ll> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    // prefix sums
    vector<ll> pref(n + 1, 0);
    for (int i = 0; i < n; i++) pref[i + 1] = pref[i] + a[i];

    // coordinate compression of prefix sums
    vector<ll> vals(pref.begin(), pref.end());
    sort(vals.begin(), vals.end());
    vals.erase(unique(vals.begin(), vals.end()), vals.end());
    int m = (int)vals.size();

    auto rank = [&](ll x) -> int {
        return (int)(lower_bound(vals.begin(), vals.end(), x) - vals.begin()) + 1; // 1-indexed
    };

    BIT bit(m);
    vector<ll> dp(n + 1, 0);

    // dp[0] = 0
    int r0 = rank(pref[0]);
    bit.update(r0, dp[0] - pref[0]); // = 0

    for (int i = 1; i <= n; i++) {
        // option 1: don't end a segment at i
        dp[i] = dp[i - 1];

        // option 2: segment ending at i, starting after j where pref[j] < pref[i]
        int ri = rank(pref[i]);
        if (ri > 1) {
            ll best = bit.query(ri - 1);
            if (best != -INF) {
                dp[i] = max(dp[i], pref[i] + best);
            }
        }

        // update BIT with current dp[i] - pref[i]
        bit.update(ri, dp[i] - pref[i]);
    }

    cout << dp[n] << '\n';
    return 0;
}
