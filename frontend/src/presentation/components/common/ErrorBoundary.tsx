import { Component, ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { hasError: boolean; message: string }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' }

  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, message: err.message }
  }

  render() {
    if (this.state.hasError)
      return (
        <div className="card text-center py-12">
          <p className="text-red-500 text-lg">❌ 오류가 발생했습니다</p>
          <p className="text-gray-400 text-sm mt-2">{this.state.message}</p>
        </div>
      )
    return this.props.children
  }
}
