FROM public.ecr.aws/lambda/python:3.11
#3.12 doesn't work

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt --upgrade

# Local Testing  
EXPOSE 8000

# Set Environment Variable 
ENV IS_USING_IMAGE_RUNTIME=True

# Copy the entire src directory
COPY src/ ${LAMBDA_TASK_ROOT}/

# ENV PYTHONPATH=${LAMBDA_TASK_ROOT}

# Set the CMD to your handler 
CMD [ "main.handler" ]