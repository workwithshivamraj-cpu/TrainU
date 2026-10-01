# TrainU browser extension

The private pilot extension targets Chrome and Edge with Manifest V3. Load the `extension/` directory as an unpacked extension from the browser's Extensions page with Developer mode enabled, then open extension options and enter your TrainU workspace origin.

Select text on a page, right-click, and choose **Ask TrainU about this selection**. TrainU opens with the selected text as a draft. Review and submit it in your workspace. The popup also links to Ask TrainU and the role-gated upload screen.

The extension declares only `contextMenus` and `storage` permissions. It has no website host permissions, content scripts, tracking, or credential collection. It does not read page contents or submit questions automatically. The workspace origin is stored in local extension storage; the selected text is limited to 2,000 characters and placed in the URL fragment rather than the request URL. The app consumes the fragment, strips it from browser history, and requires the user to submit the draft. Treat selected text as sensitive and review it before submitting.

Use HTTPS outside localhost. Authentication, organization boundaries, source visibility, and upload permission remain enforced by TrainU. The upload shortcut is not an elevated permission.

Run the URL validation suite with `npm test` from this directory. Before a Chrome Web Store or Edge Add-ons release, create and review a privacy disclosure, provide support contact details and screenshots, test current browser versions, and follow that store's current developer submission process. This repository has not been published to either store.
