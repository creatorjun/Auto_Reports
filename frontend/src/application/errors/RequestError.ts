// frontend/src/application/errors/RequestError.ts
export class RequestError extends Error {
  constructor(
    public readonly status: number | null,
    public readonly detail: unknown,
  ) {
    super(typeof detail === 'string' ? detail : 'Request failed')
    this.name = 'RequestError'
  }
}
