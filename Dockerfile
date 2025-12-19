FROM public.ecr.aws/x8v8d7g8/mars-base:latest
WORKDIR /app
COPY . .

# Install dependencies - cachetools uses setuptools
RUN pip install -e .

# Install test dependencies
RUN pip install pytest

CMD ["/bin/bash"]
