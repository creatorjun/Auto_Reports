// frontend/src/app/App.tsx
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import ThemeController from '@/presentation/components/layout/ThemeController'

export default function App() {
  return (
    <>
      <ThemeController />
      <RouterProvider router={router} />
    </>
  )
}
