---
status: resolved
trigger: "打开手机相机并手动裁剪后，有时候会卡在处理照片中一直转圈"
created: 2026-08-15
updated: 2026-08-15
---

# Mini Program photo processing stuck

## Symptoms

- Expected: 手动裁剪完成后，照片处理结束并显示确认页面；失败时给出错误且关闭 loading。
- Actual: 个别情况下停留在“处理照片中”，loading 一直旋转。
- Error messages: 用户未观察到错误提示。
- Timeline: 当前版本偶发。
- Reproduction: 打开手机相机，拍照，完成 1:1 手动裁剪。

## Current Focus

- hypothesis: 已确认代码缺少异步回调超时，任一微信图片/文件回调不结算都会让 loading 永久存在。
- test: 已为微信异步文件操作和整条处理链路加入有界超时，并用悬挂回调测试验证 loading 与 `isReading` 会恢复。
- expecting: 超时后最多等待 20 秒，显示可重试错误，不再无限转圈。
- next_action: 在微信真机上重复系统相机与手动裁剪流程，确认具体机型行为。

## Evidence

- timestamp: 2026-08-15
  observation: `loadImage` 只有进入 `finally` 才调用 `wx.hideLoading()`。
- timestamp: 2026-08-15
  observation: `getImageInfo`、`getFileInfo`、`copyFile` 均依赖微信回调，没有超时或取消路径。

## Eliminated

- hypothesis: 手动裁剪取消路径未清理 loading。
  reason: loading 仅在 `loadImage` 开始后显示，裁剪取消发生在此前。

## Resolution

- root_cause: `loadImage` 仅在 Promise 结算后进入 `finally`；`wx.getImageInfo`、`getFileInfo` 和 `copyFile` 原先均无超时，个别机型或大图场景下回调悬挂会永久保留 loading。
- fix: 底层微信操作增加 12 秒超时和一次性结算；页面增加 20 秒处理看门狗、操作 ID 防止迟到回调覆盖新状态、卸载清理及超时后的相机恢复提示。
- verification: `node --check` 通过；原始文件无损保留测试通过；悬挂微信回调的超时恢复测试通过。
- files_changed: `apps/wechat-miniapp/pages/capture/index.js`, `apps/wechat-miniapp/utils/image-reader.js`, `tests/test_wechat_manual_crop_timeout.js`
