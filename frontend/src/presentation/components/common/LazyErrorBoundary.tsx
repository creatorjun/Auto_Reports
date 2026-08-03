// frontend/src/presentation/components/common/LazyErrorBoundary.tsx
import { Component, ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { hasError: boolean }

export default class LazyErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error) {
    if (error.message.includes('Failed to fetch dynamically imported module')) {
      window.location.reload()
    }
  }

  render() {
    if (this.state.hasError) return null
    return this.props.children
  }
}
