import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 홈 디렉터리에 떠도는 package-lock.json 때문에 Turbopack 이 워크스페이스
  // 루트를 ~ 로 잘못 추론한다. 여기가 루트라고 못박는다.
  turbopack: { root: __dirname },
};

export default nextConfig;
