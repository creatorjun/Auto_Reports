// frontend/tests/filePreviewParser.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { utils, write } from 'xlsx'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const filename = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src/infrastructure/preview/filePreviewParser.ts')
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  fileName: filename,
}).outputText
const module = { exports: {} }
new Function('require', 'module', 'exports', compiled)(
  (dependency) => dependency === 'mammoth' ? require('mammoth/mammoth.browser') : require(dependency),
  module,
  module.exports,
)
const parser = module.exports.filePreviewParser

test('preview parser preserves UTF-8 and EUC-KR text decoding and invalid-byte fallback', () => {
  assert.equal(parser.decodeText(new TextEncoder().encode('안녕하세요').buffer), '안녕하세요')
  assert.equal(parser.decodeText(Uint8Array.from([190, 200, 179, 231, 199, 207, 188, 188, 191, 228]).buffer), '안녕하세요')
  assert.equal(parser.decodeText(Uint8Array.from([255]).buffer), '�')
  assert.deepEqual(parser.parseCsv(new TextEncoder().encode('제목,건수\n개선,42\n').buffer), [['제목', '건수'], ['개선', '42']])
})

test('preview parser reads every sheet of an actual Korean workbook', async () => {
  const workbook = utils.book_new()
  utils.book_append_sheet(workbook, utils.aoa_to_sheet([['제목', '건수'], ['개선 요청', 42]]), '전체 이슈')
  utils.book_append_sheet(workbook, utils.aoa_to_sheet([['필터'], ['현재 상태: 할 일']]), '적용 필터')
  const sheets = await parser.parseWorkbook(write(workbook, { type: 'array', bookType: 'xlsx' }))
  assert.deepEqual(sheets.map(({ name }) => name), ['전체 이슈', '적용 필터'])
  assert.match(sheets[0].html, /개선 요청/)
  assert.match(sheets[0].html, />42</)
  assert.match(sheets[1].html, /현재 상태: 할 일/)
})

test('preview parser converts an actual DOCX package using the installed document library', async () => {
  const fixture = 'UEsDBBQAAAAIAAAARl26d6SczQAAAFMBAAATAAAAW0NvbnRlbnRfVHlwZXNdLnhtbJWQMVLEMAxFr+Jxy6wdKCiYJFsALVBwAY2jJB4s2WNpg7k9k13Ygo5a7//3R/2xUTIbVomZB3vrOnsc+/evgmIaJZbBrqrlwXsJKxKIywW5UZpzJVBxuS6+QPiABf1d1937kFmR9aB7hx37J5zhlNQ8N0W+WComsebxAu6uwUIpKQbQmNlvPP2xHH4MrmI6M7LGIjeNkvVj/7phrXFC8wZVX4BwsP4z18lPOZwIWd0O/suX5zkGvOb3tlJzQJHICyV3vRBE/t3hz28bvwFQSwMEFAAAAAgAAABGXV8zlVKXAAAABwEAAAsAAABfcmVscy8ucmVsc43PsQ7CIBQF0F8h7wP6WgcHU9rFpavpDxB4bYnAI4CKf+/iYI2D683Nubn9WL0Td0rZcpDQNS2MQ38hp4rlkDcbs6jehSxhKyWeELPeyKvccKRQvVs4eVVyw2nFqPRVrYSHtj1i+jRgb4rJSEiT6UDMz0j/2LwsVtOZ9c1TKD8mvhogZpVWKhIenAyad9xU7wCHHncXhxdQSwMEFAAAAAgAAABGXSvR6BWhAAAAwQAAABEAAAB3b3JkL2RvY3VtZW50LnhtbEXOPw6CMBgF8Ks0PQBFBwfCn7NgqUDSr1/TVsHNwWPoykSiUQfORDmEKQ4uvze85OWlRQ+SnISxLaqMbqKYFnnaJRXyIwjlSA9S2aTLaOOcThizvBFQ2gi1UD3IAxoonY3Q1KxDU2mDXFjbqhok28bxjkHZKhom91idQ+qACbjcj9NyvRH/mPww+vdnnp5kfl2W4Z6y0AfNql79bbD/v/wLUEsBAhQAFAAAAAgAAABGXbp3pJzNAAAAUwEAABMAAAAAAAAAAAAAAIABAAAAAFtDb250ZW50X1R5cGVzXS54bWxQSwECFAAUAAAACAAAAEZdXzOVUpcAAAAHAQAACwAAAAAAAAAAAAAAgAH+AAAAX3JlbHMvLnJlbHNQSwECFAAUAAAACAAAAEZdK9HoFaEAAADBAAAAEQAAAAAAAAAAAAAAgAG+AQAAd29yZC9kb2N1bWVudC54bWxQSwUGAAAAAAMAAwC5AAAAjgIAAAAA'
  const buffer = Buffer.from(fixture, 'base64')
  const html = await parser.parseDocument(buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength))
  assert.equal(html, '<p>문서 미리보기 검증</p>')
})
