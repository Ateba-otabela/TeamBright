import { createBrowserRouter } from 'react-router-dom'

import RootLayout from '@/app/layouts/RootLayout'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: null,
      },
      {
        path: '*',
        element: null,
      },
    ],
  },
])
