# Task: Cascade Chain + Investigate Banner

## Feature 1: Cascade Chain (Markaz Web)
- [x] Create `CascadeChain.tsx` component with Framer Motion animations
- [x] Add `cascade_risks` to Crisis interface in `IncidentsTable.tsx`
- [x] Add click-to-expand row with CascadeChain rendering
- [x] Add `cascade_risks` to Crisis interface in `page.tsx`
- [x] ESLint clean: 0 errors, 0 warnings
- [x] Build clean: `npm run build` passes

## Feature 2: Investigation Banner (Nigraan Mobile)
- [x] Extract `status` from crisis object
- [x] Add yellow amber banner for `investigate` status or `detected` with conf < 50%
- [x] Banner text: "⏳ Awaiting Nigraan Verification" + confidence % + Urdu
- [x] `flutter analyze`: No issues found

## Build & Deploy
- [x] Nigraan APK: 52.8MB ✅
- [x] Awaaz APK: 51.7MB ✅
- [x] APKs copied to Desktop + project dir
- [x] Web static export copied to backend/web
- [x] Cloud Run deployed: revision `tapish-backend-00060-hbd`, 100% traffic
