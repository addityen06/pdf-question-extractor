Place any fixture PDF files here for integration tests.

For the pipeline integration test to run, create a file named:

    tests/fixtures/sample_paper.pdf

This should be a real exam paper PDF. It does not need to be one of the
production papers. Any structured document with numbered questions will work.

The integration tests skip automatically if this file is not present.
