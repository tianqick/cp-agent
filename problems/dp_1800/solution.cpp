#include <iostream>
#include <vector>
#include <algorithm>
#include <cstring>
#include <cmath>
using namespace std;

const int MAXN = 200005;

int n, k;
int a[MAXN];
vector<long long> vals;
int dp[MAXN];

// 线段树，维护区间最大值
int tree[4 * MAXN];

void update(int node, int l, int r, int pos, int val) {
    if (l == r) {
        tree[node] = max(tree[node], val);
        return;
    }
    int mid = (l + r) / 2;
    if (pos <= mid) update(2*node, l, mid, pos, val);
    else update(2*node+1, mid+1, r, pos, val);
    tree[node] = max(tree[2*node], tree[2*node+1]);
}

int query(int node, int l, int r, int ql, int qr) {
    if (qr < l || ql > r) return 0;
    if (ql <= l && r <= qr) return tree[node];
    int mid = (l + r) / 2;
    return max(query(2*node, l, mid, ql, qr),
               query(2*node+1, mid+1, r, ql, qr));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> k;
    for (int i = 0; i < n; i++) {
        cin >> a[i];
        vals.push_back(a[i]);
        // 将边界值加入离散化（注意用 long long 防溢出）
        long long lo = (long long)a[i] - k;
        long long hi = (long long)a[i] + k;
        if (lo >= 1) vals.push_back(lo);
        else vals.push_back(1);
        if (hi <= 1000000000) vals.push_back(hi);
        else vals.push_back(1000000000);
    }

    // 离散化
    sort(vals.begin(), vals.end());
    vals.erase(unique(vals.begin(), vals.end()), vals.end());

    int m = vals.size();
    int ans = 0;
    memset(tree, 0, sizeof(tree));

    for (int i = 0; i < n; i++) {
        // 查询区间 [a[i]-k, a[i]+k] 的最大值
        long long lo = (long long)a[i] - k;
        long long hi = (long long)a[i] + k;
        if (lo < 1) lo = 1;
        if (hi > 1000000000) hi = 1000000000;
        
        int l = (int)(lower_bound(vals.begin(), vals.end(), lo) - vals.begin());
        int r = (int)(upper_bound(vals.begin(), vals.end(), hi) - vals.begin()) - 1;
        
        int best = 0;
        if (l <= r) {
            best = query(1, 0, m - 1, l, r);
        }
        dp[i] = best + 1;
        ans = max(ans, dp[i]);
        
        // 更新线段树
        int pos = (int)(lower_bound(vals.begin(), vals.end(), (long long)a[i]) - vals.begin());
        update(1, 0, m - 1, pos, dp[i]);
    }

    cout << ans << "\n";

    return 0;
}