# 0003. InterviewLog を MVP では実装しない

**状況**: 面接の記録は有用だが、MVP では Stage の `memo` で足りる。

**決定**: InterviewLog はドメイン・ユースケース・UI・MCP ツールから外し、Stage の `memo` に書く運用とする。

**結果**: Stage は ID を持つエンティティのままなので、後から `ApplicationId + StageId` の参照で追加できる。
